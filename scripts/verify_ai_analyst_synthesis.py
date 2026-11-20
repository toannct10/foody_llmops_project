"""Run the four Hanuri analyst questions without changing frozen evaluations."""

import argparse
import json

from src.rag.schemas import RetrievalRequest
from src.rag.service import resolve_restaurant
from src.rag_v3.cli import selected_v3_gateway
from src.rag_v3.retriever import RoutedRetriever
from src.rag_v3.service import answer_question_v3

RESTAURANT = "Hanuri - Quán Ăn Hàn Quốc - Nguyễn Đình Chiểu"
QUESTIONS = {
    "A": "Nhân viên phục vụ có vấn đề gì không?",
    "B": "Khách nói gì về chất lượng món ăn?",
    "C": "Khách có phàn nàn về giá không?",
    "D": "Tại sao đánh giá của nhà hàng này giảm?",
}


def run(cases, show_audit=False):
    key, _ = resolve_restaurant(RESTAURANT)
    retriever = RoutedRetriever()
    results = []
    with selected_v3_gateway() as gateway:
        for case in cases:
            question = QUESTIONS[case]
            audit = []
            response, hits, telemetry, debug, packet = answer_question_v3(
                retriever, gateway,
                RetrievalRequest(query=question, restaurant_key=key, top_k=5),
                generation_audit=audit,
            )
            row = {
                "case": case,
                "question": question,
                "answer": response.answer,
                "mode": response.generation_mode,
                "route": response.query_route,
                "retrieval_method": debug["retrieval_method"],
                "retrieved_count": len(hits),
                "packet_count": len(packet.evidence),
                "cited_refs": [item["ref"] for item in packet.evidence
                               if item["review_id"] in {
                                   evidence.review_id for evidence in response.evidence
                               }],
                "citation_valid": telemetry["citation_success"],
                "support_status": telemetry["clause_support_status"],
                "generation_attempts": telemetry["generation_attempts"],
                "failure_category": telemetry["failure_category"],
                "input_tokens": telemetry["input_tokens"],
                "output_tokens": telemetry["output_tokens"],
            }
            if show_audit:
                row["generation_audit"] = audit
                row["evidence"] = list(packet.evidence)
            results.append(row)
            print(json.dumps(row, ensure_ascii=False, indent=2), flush=True)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("cases", nargs="*", choices=tuple(QUESTIONS), default=list(QUESTIONS))
    parser.add_argument("--show-audit", action="store_true")
    args = parser.parse_args()
    run(args.cases, args.show_audit)
