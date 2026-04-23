# Lab 16 Benchmark Report

## Metadata
- Dataset: hotpot_100.json
- Mode: mock
- Records: 200
- Agents: react, reflexion

## Summary
| Metric | ReAct | Reflexion | Delta |
|---|---:|---:|---:|
| EM | 1.0 | 0.99 | -0.01 |
| Avg attempts | 1 | 1.02 | 0.02 |
| Avg token estimate | 204.66 | 208.85 | 4.19 |
| Avg latency (ms) | 3841.14 | 2456.43 | -1384.71 |

## Failure modes
```json
{
  "react": {
    "none": 100
  },
  "reflexion": {
    "none": 99,
    "wrong_final_answer": 1
  }
}
```

## Extensions implemented
- structured_evaluator
- reflection_memory
- benchmark_report_json
- mock_mode_for_autograding

## Discussion
Reflexion helps when the first attempt stops after the first hop or drifts to a wrong second-hop entity. The tradeoff is higher attempts, token cost, and latency. In a real report, students should explain when the reflection memory was useful, which failure modes remained, and whether evaluator quality limited gains.
