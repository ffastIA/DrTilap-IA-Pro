"""Executor de avaliação de qualidade do RAG.

Mede recuperação (barato, determinístico) e, opcionalmente, geração (caro).
Cada execução é salva com a configuração vigente, para que duas execuções sejam
comparáveis — foi justamente a ausência disso que permitiu que as regressões de
embedding e chunking passassem despercebidas.

Uso:
    python -m evaluation.run_eval --retrieval-only
    python -m evaluation.run_eval --full
    python -m evaluation.run_eval --compare runs/a.json runs/b.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from langchain_community.callbacks.manager import get_openai_callback

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evaluation.metrics import (  # noqa: E402
    is_refusal,
    mention_coverage,
    passage_rank,
)

EVAL_DIR = Path(__file__).resolve().parent
GOLDEN_SET_PATH = EVAL_DIR / "golden_set.yaml"
RUNS_DIR = EVAL_DIR / "runs"

# Preços em USD por 1M de tokens. Fonte: tabela pública da OpenAI.
# Mantidos em um único lugar visível — se ficarem desatualizados, o custo
# reportado fica errado de forma silenciosa.
PRICING_USD_PER_1M = {
    "text-embedding-ada-002": {"input": 0.10},
    "text-embedding-3-small": {"input": 0.02},
    "text-embedding-3-large": {"input": 0.13},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
}


# --------------------------------------------------------------------- config

def capture_config(service: Any) -> dict:
    """Fotografa a configuração efetiva do RAG.

    Lê os valores REAIS dos objetos, não os presumidos: o modelo de embedding
    atual vem de um default implícito da biblioteca, e é exatamente esse tipo
    de divergência entre o presumido e o efetivo que precisamos flagrar.
    """
    embeddings = service.embeddings
    splitter = service.text_splitter
    return {
        "embedding_model": getattr(embeddings, "model", "desconhecido"),
        "embedding_dimensions": getattr(embeddings, "dimensions", None),
        "chunk_size": getattr(splitter, "_chunk_size", None),
        "chunk_overlap": getattr(splitter, "_chunk_overlap", None),
        "similarity_threshold": getattr(service, "similarity_threshold", None),
        "llm_model": getattr(service.llm, "model_name", None),
    }


# ------------------------------------------------------------------ execution

def evaluate_retrieval(service: Any, question: dict, k: int, use_llm_expansion: bool) -> dict:
    started = time.perf_counter()
    docs = service._retrieve_docs_via_rpc(
        question["question"], k=k, use_llm_expansion=use_llm_expansion
    )
    elapsed = time.perf_counter() - started

    contents = [doc.page_content for doc in docs]
    similarities = [doc.metadata.get("similarity", 0.0) for doc in docs]

    expected = question.get("expected_passages") or []
    ranks = {passage: passage_rank(passage, contents) for passage in expected}
    found = [p for p, r in ranks.items() if r is not None]
    missed = [p for p, r in ranks.items() if r is None]

    return {
        "retrieved_count": len(docs),
        "top_similarity": max(similarities) if similarities else 0.0,
        "min_similarity": min(similarities) if similarities else 0.0,
        "expected_total": len(expected),
        "expected_found": len(found),
        "recall": (len(found) / len(expected)) if expected else None,
        "first_hit_rank": min((r for r in ranks.values() if r is not None), default=None),
        "missed_passages": missed,
        "retrieval_seconds": round(elapsed, 3),
    }


def evaluate_generation(service: Any, question: dict, judge: Any) -> dict:
    started = time.perf_counter()
    answer = service.get_answer(question["question"], question.get("history") or [])
    elapsed = time.perf_counter() - started

    refused = is_refusal(answer)
    out_of_corpus = question["scope"] == "out_of_corpus"

    result = {
        "answer_chars": len(answer),
        "refused": refused,
        # Para out_of_corpus, o acerto é recusar. Para in_corpus, é NÃO recusar.
        "refusal_correct": refused if out_of_corpus else (not refused),
        "mention_coverage": (
            None if out_of_corpus else mention_coverage(answer, question.get("must_mention") or [])
        ),
        "generation_seconds": round(elapsed, 3),
        "answer": answer,
    }

    if judge is not None and not out_of_corpus:
        result["groundedness"] = judge(question["question"], answer)
    return result


def build_judge(service: Any):
    """Juiz de embasamento, isolado da geração (decisão 3 do design).

    Recupera o contexto novamente e pergunta a um modelo se a resposta se
    sustenta nele. Não reaproveita a chamada que gerou a resposta.
    """
    from langchain_core.messages import HumanMessage, SystemMessage

    system = SystemMessage(content=(
        "Você avalia se uma resposta está embasada no contexto fornecido. "
        "Responda APENAS com um número de 0 a 100, sem texto adicional. "
        "100 = toda afirmação da resposta se sustenta no contexto. "
        "0 = a resposta é inventada. "
        "Penalize números que não aparecem no contexto."
    ))

    def judge(question: str, answer: str) -> float | None:
        docs = service._retrieve_docs_via_rpc(question, k=20, use_llm_expansion=False)
        context = "\n\n".join(doc.page_content for doc in docs)
        message = HumanMessage(content=(
            f"CONTEXTO:\n{context[:20000]}\n\n"
            f"PERGUNTA: {question}\n\nRESPOSTA:\n{answer}\n\n"
            "Nota de embasamento (0-100):"
        ))
        try:
            raw = service.llm.invoke([system, message]).content
            digits = "".join(ch for ch in raw if ch.isdigit())
            return float(digits[:3]) if digits else None
        except Exception as exc:  # noqa: BLE001
            print(f"    [aviso] juiz falhou: {exc}")
            return None

    return judge


# -------------------------------------------------------------------- summary

def estimate_embedding_calls(question_count: int, use_llm_expansion: bool, full: bool) -> int:
    """Estimativa de chamadas de embedding, que o callback do LangChain não cobre.

    Uma por recuperação. No modo completo há a recuperação da avaliação, mais a
    de dentro do `get_answer` (com possíveis retries) e a do juiz.
    """
    per_question = 1
    if full:
        per_question += 2  # get_answer + juiz (sem contar retries)
    return question_count * per_question


def summarize(results: list[dict]) -> dict:
    in_corpus = [r for r in results if r["scope"] == "in_corpus"]
    out_corpus = [r for r in results if r["scope"] == "out_of_corpus"]

    recalls = [r["retrieval"]["recall"] for r in in_corpus
               if r.get("retrieval") and r["retrieval"]["recall"] is not None]
    top_sims = [r["retrieval"]["top_similarity"] for r in results if r.get("retrieval")]

    summary: dict[str, Any] = {
        "questions_total": len(results),
        "questions_in_corpus": len(in_corpus),
        "questions_out_of_corpus": len(out_corpus),
        "mean_recall": round(statistics.mean(recalls), 3) if recalls else None,
        "perfect_recall_rate": (
            round(sum(1 for r in recalls if r == 1.0) / len(recalls), 3) if recalls else None
        ),
        "mean_top_similarity": round(statistics.mean(top_sims), 3) if top_sims else None,
    }

    generated = [r for r in results if r.get("generation")]
    if generated:
        correct_refusals = [r["generation"]["refusal_correct"] for r in generated]
        summary["refusal_correct_rate"] = round(sum(correct_refusals) / len(correct_refusals), 3)

        oos_generated = [r for r in out_corpus if r.get("generation")]
        if oos_generated:
            summary["out_of_corpus_refusal_rate"] = round(
                sum(1 for r in oos_generated if r["generation"]["refused"]) / len(oos_generated), 3
            )

        grounds = [r["generation"].get("groundedness") for r in generated]
        grounds = [g for g in grounds if g is not None]
        if grounds:
            summary["mean_groundedness"] = round(statistics.mean(grounds), 1)

        coverages = [r["generation"].get("mention_coverage") for r in generated]
        coverages = [c for c in coverages if c is not None]
        if coverages:
            summary["mean_mention_coverage"] = round(statistics.mean(coverages), 3)

    return summary


def print_report(run: dict) -> None:
    print("\n" + "=" * 78)
    print(f"Execução: {run['run_id']}   modo: {run['mode']}")
    print("=" * 78)
    cfg = run["config"]
    print(f"  embedding      : {cfg['embedding_model']} (dims={cfg['embedding_dimensions']})")
    print(f"  chunk          : size={cfg['chunk_size']} overlap={cfg['chunk_overlap']}")
    print(f"  threshold      : {cfg['similarity_threshold']}   k={run['k']}")
    print(f"  llm            : {cfg['llm_model']}")
    print("-" * 78)
    print(f"{'id':<26}{'recall':>8}{'top_sim':>9}{'rank':>6}{'recusa':>9}")
    print("-" * 78)
    for r in run["results"]:
        ret = r.get("retrieval") or {}
        gen = r.get("generation") or {}
        recall = ret.get("recall")
        recall_text = "—" if recall is None else f"{recall:.2f}"
        rank = ret.get("first_hit_rank")
        rank_text = "—" if rank is None else str(rank)
        if gen:
            refusal = "OK" if gen["refusal_correct"] else "FALHA"
        else:
            refusal = "—"
        print(f"{r['id']:<26}{recall_text:>8}{ret.get('top_similarity', 0):>9.3f}"
              f"{rank_text:>6}{refusal:>9}")

    print("-" * 78)
    for key, value in run["summary"].items():
        print(f"  {key:<28} {value}")

    cost = run.get("cost") or {}
    if cost:
        latencies = [
            (r.get("retrieval") or {}).get("retrieval_seconds", 0)
            + (r.get("generation") or {}).get("generation_seconds", 0)
            for r in run["results"]
        ]
        print(f"\n  custo LLM (USD)              {cost.get('llm_cost_usd')}"
              f"  em {cost.get('llm_calls')} chamadas")
        print(f"  embeddings (estimados)       {cost.get('embedding_calls_estimated')} chamadas")
        if latencies:
            print(f"  latência média/pergunta      {statistics.mean(latencies):.2f}s")
    misses = [(r["id"], p) for r in run["results"]
              for p in (r.get("retrieval") or {}).get("missed_passages", [])]
    if misses:
        print(f"\n  Trechos não recuperados ({len(misses)}):")
        for qid, passage in misses:
            print(f"    [{qid}] {passage[:70]}")
    print("=" * 78 + "\n")


def compare(path_a: Path, path_b: Path) -> None:
    run_a = json.loads(path_a.read_text(encoding="utf-8"))
    run_b = json.loads(path_b.read_text(encoding="utf-8"))

    print("\n" + "=" * 78)
    print(f"Comparação:  A={run_a['run_id']}   B={run_b['run_id']}")
    print("=" * 78)

    print("\nConfiguração:")
    # `k`, o modo e a expansão de query fazem parte da configuração de recuperação
    # tanto quanto o modelo — sem eles, uma comparação pode esconder o que mudou.
    config_a = {**run_a["config"], "k": run_a.get("k"),
                "llm_expansion": run_a.get("llm_expansion"), "mode": run_a.get("mode")}
    config_b = {**run_b["config"], "k": run_b.get("k"),
                "llm_expansion": run_b.get("llm_expansion"), "mode": run_b.get("mode")}
    keys = sorted(set(config_a) | set(config_b))
    for key in keys:
        va, vb = config_a.get(key), config_b.get(key)
        marker = "  " if va == vb else "->"
        print(f" {marker} {key:<24} {va}  |  {vb}")

    print("\nMétricas:")
    keys = sorted(set(run_a["summary"]) | set(run_b["summary"]))
    for key in keys:
        va, vb = run_a["summary"].get(key), run_b["summary"].get(key)
        delta = ""
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            diff = vb - va
            delta = f"   ({diff:+.3f})" if diff else "   (=)"
        print(f"    {key:<28} {va}  |  {vb}{delta}")
    print("=" * 78 + "\n")


# ----------------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser(description="Avaliação de qualidade do RAG")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--retrieval-only", action="store_true",
                      help="Só métricas de recuperação (barato, determinístico)")
    mode.add_argument("--full", action="store_true",
                      help="Recuperação + geração + juiz de embasamento (caro)")
    mode.add_argument("--compare", nargs=2, metavar=("RUN_A", "RUN_B"),
                      help="Compara duas execuções salvas")
    parser.add_argument("--k", type=int, default=20, help="Documentos recuperados (default: 20)")
    parser.add_argument("--no-llm-expansion", action="store_true",
                        help="Desliga a expansão de query por LLM (mais barato e determinístico)")
    parser.add_argument("--label", default="", help="Rótulo para identificar a execução")
    args = parser.parse_args()

    if args.compare:
        compare(Path(args.compare[0]), Path(args.compare[1]))
        return 0

    from app.services.rag_service import get_rag_service

    service = get_rag_service()
    spec = yaml.safe_load(GOLDEN_SET_PATH.read_text(encoding="utf-8"))
    questions = spec["questions"]
    use_llm_expansion = not args.no_llm_expansion
    judge = build_judge(service) if args.full else None

    print(f"Avaliando {len(questions)} perguntas "
          f"(modo={'full' if args.full else 'retrieval-only'}, k={args.k}, "
          f"expansão_llm={use_llm_expansion})...\n")

    results = []
    with get_openai_callback() as usage:
        for index, question in enumerate(questions, start=1):
            print(f"  [{index}/{len(questions)}] {question['id']}")
            entry = {
                "id": question["id"],
                "scope": question["scope"],
                "question_type": question.get("question_type"),
                "question": question["question"],
            }
            try:
                entry["retrieval"] = evaluate_retrieval(
                    service, question, args.k, use_llm_expansion
                )
                if args.full:
                    entry["generation"] = evaluate_generation(service, question, judge)
            except Exception as exc:  # noqa: BLE001
                entry["error"] = f"{type(exc).__name__}: {exc}"
                print(f"    [erro] {entry['error']}")
            results.append(entry)

    # O callback do LangChain contabiliza apenas chamadas de chat (geração,
    # expansão de query e juiz). Embeddings NÃO entram nesta conta — são
    # estimados à parte, pelo número de consultas embutidas.
    cost = {
        "llm_calls": usage.successful_requests,
        "llm_prompt_tokens": usage.prompt_tokens,
        "llm_completion_tokens": usage.completion_tokens,
        "llm_cost_usd": round(usage.total_cost, 4),
        "embedding_calls_estimated": estimate_embedding_calls(
            len(questions), use_llm_expansion, args.full
        ),
        "note": "Custo de embeddings não incluído (callback do LangChain cobre só chat).",
    }

    run = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "label": args.label,
        "mode": "full" if args.full else "retrieval-only",
        "k": args.k,
        "llm_expansion": use_llm_expansion,
        "golden_set_version": spec.get("version"),
        "config": capture_config(service),
        "cost": cost,
        "results": results,
        "summary": summarize(results),
    }

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    suffix = f"-{args.label}" if args.label else ""
    output = RUNS_DIR / f"{run['run_id']}{suffix}.json"
    output.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")

    print_report(run)
    print(f"Salvo em: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
