from deepeval import evaluate
from deepeval.test_case import LLMTestCase
from deepeval.metrics import(
    FaithfulnessMetric,
    AnswerRelevancyMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,

)

from eval.groq_judge import GroqModel
from eval.test_cases import TEST_CASES
from retrieval.hybrid_search import hybrid_search
from graph.expand import expand_with_graph
from generation.ask import ask_question

judge = GroqModel()

def run_evaluation():
    results_summary = []

    for case in [TEST_CASES[0]]:
        question = case["question"]
        repo = case["repo"]

        #Run for real pipeline
        search_results = hybrid_search(question, repo)
        top_chunks = [chunk for chunk, score in search_results] 
        expanded_chunks = expand_with_graph(top_chunks,repo_name=repo)
        actual_answer = ask_question( question, expanded_chunks)

        retrieval_context = [c.payload["content"] for c in expanded_chunks]
        retreved_paths = [c.payload["path"] for c in expanded_chunks]


        # Create a test case for evaluation
        test_case = LLMTestCase(
            input=question,
            actual_output=actual_answer,
            expected_output=case["expected_answer"],
            retrieval_context=retrieval_context,
        )

        # Evaluate the test case using various metrics
        metrics = [
            FaithfulnessMetric(threshold=0.7,model=judge,include_reason =True),
            AnswerRelevancyMetric(threshold=0.7,model=judge,include_reason =True),
            ContextualPrecisionMetric(threshold=0.7,model=judge,include_reason =True),
            ContextualRecallMetric(threshold=0.7,model=judge,include_reason =True),
        ]

        case_result = {
            "question" : question,
            "expected_chunk_found" : case["expected_chunk_path"] in retreved_paths,
            "scores" : {},   
       }

        for metric in metrics:
            metric.measure(test_case)
            case_result["scores"][metric.__class__.__name__] = {
                "score" : metric.score,
                "reason" : metric.reason,
            }

        results_summary.append(case_result)

    return results_summary

if __name__ == "__main__":
    results = run_evaluation()
    for r in results:
        print(f"\n=== {r['question']} ===")
        print(f"Expected chunk retrieved: {r['expected_chunk_found']}")
        for metric_name, data in r["scores"].items():
            print(f"  {metric_name}: {data['score']:.2f} — {data['reason'][:100]}")