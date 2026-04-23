# Lab 16 Benchmark Report

## Metadata
- Dataset: hotpot_mini.json
- Mode: mock
- Records: 16
- Agents: react, reflexion

## Summary
| Metric | ReAct | Reflexion | Delta |
|---|---:|---:|---:|
| EM | 0.875 | 1.0 | 0.125 |
| Avg attempts | 1 | 1 | 0 |
| Avg token estimate | 208.38 | 211.62 | 3.24 |
| Avg latency (ms) | 58168.75 | 3034.75 | -55134.0 |

## Failure modes
```json
{
  "react": {
    "none": 7,
    "wrong_final_answer": 1
  },
  "reflexion": {
    "none": 8
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
