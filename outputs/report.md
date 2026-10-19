## Summary table

| Run | Strategy | Correct /20 | Unanswered | Input tokens | Output tokens | Median seconds per question | Total seconds | Cost ($) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | S1 direct | 4 | 2 | 45,540 | 564 | 1.3 | 31.1 | 0.0098 |
| 1 | S2 think and vote (k = 5) | 15 | 0 | 228,400 | 9,551 | 8.7 | 185.4 | 0.0571 |
| 1 | S3 tools | 18 | 0 | 68,393 | 3,808 | 4.5 | 95.4 | 0.0182 |
| 2 | S1 direct | 5 | 2 | 45,540 | 582 | 1.2 | 30.1 | 0.0098 |
| 2 | S2 think and vote (k = 5) | 18 | 0 | 228,400 | 9,487 | 8.4 | 173.3 | 0.0571 |
| 2 | S3 tools | 18 | 0 | 70,897 | 3,869 | 4.8 | 103.9 | 0.0188 |

## Per question (run 1)

| Question | S1 | S2 | S3 |
|---|:---:|:---:|:---:|
| Q-01 | ✗ | ✓ | ✓ |
| Q-02 | ✗ | ✓ | ✓ |
| Q-03 | ✗ | ✓ | ✓ |
| Q-04 | ✓ | ✓ | ✓ |
| Q-05 | ✗ | ✗ | ✓ |
| Q-06 | ✗ | ✓ | ✓ |
| Q-07 | ✗ | ✓ | ✓ |
| Q-08 | ✗ | ✓ | ✓ |
| Q-09 | ✗ | ✓ | ✓ |
| Q-10 | ✓ | ✓ | ✓ |
| Q-11 | ✗ | ✓ | ✓ |
| Q-12 | ✗ | ✓ | ✓ |
| Q-13 | ✗ | ✓ | ✓ |
| Q-14 | ✗ | ✗ | ✓ |
| Q-15 | ✗ | ✗ | ✓ |
| Q-16 | ✓ | ✓ | ✓ |
| Q-17 | ✓ | ✗ | ✗ |
| Q-18 | ✗ | ✓ | ✓ |
| Q-19 | ✗ | ✓ | ✓ |
| Q-20 | ✗ | ✗ | ✗ |

## Wrong or unanswered answers (for C2)

- run 1 S1 Q-01: model answer None, expected Ossbridge | 4.6
- run 1 S1 Q-02: model answer ['harrowfield', 0.98], expected Harrowfield | 1.69
- run 1 S1 Q-03: model answer ['lindenmoor', 0.5], expected Lindenmoor | 5.3
- run 1 S1 Q-05: model answer ['coldharbour', 3.0], expected Coldharbour | 14235
- run 1 S1 Q-06: model answer ['yes', 8071.0], expected yes | 14069
- run 1 S1 Q-07: model answer ['coldharbour', 32.07], expected Coldharbour | 18.5
- run 1 S1 Q-08: model answer ['brightwater', 72.39], expected Brightwater | 72.46
- run 1 S1 Q-09: model answer ['brightwater', 0.4], expected Millbrook | 0.6
- run 1 S1 Q-11: model answer ['redfen', 194.03], expected Redfen | 56.1
- run 1 S1 Q-12: model answer ['harrowfield', 0.7], expected Tarnvale | 64.4
- run 1 S1 Q-13: model answer None, expected Coldharbour | 4.16
- run 1 S1 Q-14: model answer ['ashgrove', 0.0], expected Ashgrove | 4.9
- run 1 S1 Q-15: model answer ['redfen', 18.34], expected Redfen | 17.61
- run 1 S1 Q-18: model answer ['yes', 39994.0], expected yes | 40013
- run 1 S1 Q-19: model answer ['redfen', 0.033], expected Lindenmoor | 0.035
- run 1 S1 Q-20: model answer ['harrowfield', 36.0], expected Ashgrove | 2993
- run 1 S2 Q-05: model answer ['coldharbour', 14222.0], expected Coldharbour | 14235, votes [{'answer': ['coldharbour', 14222.0], 'votes': 1}, {'answer': ['coldharbour', 14338.0], 'votes': 1}, {'answer': ['coldharbour', 14296.0], 'votes': 1}, {'answer': ['coldharbour', 14345.0], 'votes': 1}, {'answer': ['coldharbour', 14346.0], 'votes': 1}]
- run 1 S2 Q-14: model answer ['ashgrove', 4.7], expected Ashgrove | 4.9, votes [{'answer': ['ashgrove', 4.7], 'votes': 2}, {'answer': ['tarnvale', 0.0], 'votes': 1}, {'answer': ['tarnvale', 0.2], 'votes': 1}, {'answer': ['ashgrove', 0.0], 'votes': 1}]
- run 1 S2 Q-15: model answer ['redfen', 17.97], expected Redfen | 17.61, votes [{'answer': ['redfen', 17.97], 'votes': 2}, {'answer': ['redfen', 18.7], 'votes': 1}, {'answer': ['redfen', 17.79], 'votes': 1}, {'answer': ['redfen', 17.61], 'votes': 1}]
- run 1 S2 Q-17: model answer ['harrowfield', 887.0], expected Harrowfield | 884, votes [{'answer': ['harrowfield', 887.0], 'votes': 2}, {'answer': ['harrowfield', 884.0], 'votes': 1}, {'answer': ['harrowfield', 889.0], 'votes': 1}, {'answer': ['harrowfield', 886.0], 'votes': 1}]
- run 1 S2 Q-20: model answer ['ashgrove', 3005.0], expected Ashgrove | 2993, votes [{'answer': ['ashgrove', 3005.0], 'votes': 1}, {'answer': ['ashgrove', 2968.0], 'votes': 1}, {'answer': ['ashgrove', 2989.0], 'votes': 1}, {'answer': ['ashgrove', 2997.0], 'votes': 1}, {'answer': ['ashgrove', 3003.0], 'votes': 1}]
- run 1 S3 Q-17: model answer ['harrowfield', 14697.0], expected Harrowfield | 884
- run 1 S3 Q-20: model answer ['ashgrove', 890.0], expected Ashgrove | 2993
- run 2 S1 Q-02: model answer None, expected Harrowfield | 1.69
- run 2 S1 Q-05: model answer ['stonecairn', 6.0], expected Coldharbour | 14235
- run 2 S1 Q-06: model answer ['yes', 8169.0], expected yes | 14069
- run 2 S1 Q-07: model answer ['coldharbour', 3.63], expected Coldharbour | 18.5
- run 2 S1 Q-08: model answer ['brightwater', 72.38], expected Brightwater | 72.46
- run 2 S1 Q-09: model answer ['brightwater', 0.2], expected Millbrook | 0.6
- run 2 S1 Q-11: model answer ['redfen', 67.94], expected Redfen | 56.1
- run 2 S1 Q-12: model answer ['harrowfield', 1152.0], expected Tarnvale | 64.4
- run 2 S1 Q-13: model answer None, expected Coldharbour | 4.16
- run 2 S1 Q-14: model answer ['tarnvale', 6.2], expected Ashgrove | 4.9
- run 2 S1 Q-15: model answer ['redfen', 24.7], expected Redfen | 17.61
- run 2 S1 Q-17: model answer ['harrowfield', 37.0], expected Harrowfield | 884
- run 2 S1 Q-18: model answer ['yes', 399.0], expected yes | 40013
- run 2 S1 Q-19: model answer ['redfen', 0.058], expected Lindenmoor | 0.035
- run 2 S1 Q-20: model answer ['harrowfield', 85.0], expected Ashgrove | 2993
- run 2 S2 Q-05: model answer ['coldharbour', 14324.0], expected Coldharbour | 14235, votes [{'answer': ['coldharbour', 14324.0], 'votes': 1}, {'answer': ['coldharbour', 14352.0], 'votes': 1}, {'answer': ['coldharbour', 14354.0], 'votes': 1}, {'answer': ['coldharbour', 14288.0], 'votes': 1}, {'answer': ['coldharbour', 14333.0], 'votes': 1}]
- run 2 S2 Q-20: model answer ['ashgrove', 2975.0], expected Ashgrove | 2993, votes [{'answer': ['ashgrove', 2975.0], 'votes': 1}, {'answer': ['ashgrove', 2990.0], 'votes': 1}, {'answer': ['ashgrove', 2886.0], 'votes': 1}, {'answer': ['ashgrove', 2873.0], 'votes': 1}, {'answer': ['ashgrove', 2993.0], 'votes': 1}]
- run 2 S3 Q-08: model answer ['brightwater', 72456.15], expected Brightwater | 72.46
- run 2 S3 Q-20: model answer ['ashgrove', 890.0], expected Ashgrove | 2993

## Most expensive question per strategy (for C2)

- run 1 S1: Q-17 with 2,283 input and 93 output tokens
- run 1 S2: Q-08 with 11,430 input and 747 output tokens
- run 1 S3: Q-11 with 4,775 input and 266 output tokens
- run 2 S1: Q-03 with 2,277 input and 113 output tokens
- run 2 S2: Q-08 with 11,430 input and 735 output tokens
- run 2 S3: Q-11 with 4,775 input and 266 output tokens

## S3 rounds and tool calls (run 1, for the final questions)

| Question | Rounds | Tool calls | Input tokens per round |
|---|---:|---:|---|
| Q-01 | 3 | 7 | 821, 1102, 1287 |
| Q-02 | 3 | 5 | 827, 1105, 1188 |
| Q-03 | 4 | 7 | 827, 1156, 1303, 1370 |
| Q-04 | 4 | 7 | 822, 1078, 1184, 1245 |
| Q-05 | 3 | 5 | 823, 1115, 1205 |
| Q-06 | 3 | 4 | 827, 1042, 1099 |
| Q-07 | 3 | 5 | 831, 1121, 1214 |
| Q-08 | 3 | 4 | 829, 1073, 1155 |
| Q-09 | 3 | 7 | 821, 1121, 1298 |
| Q-10 | 3 | 3 | 818, 970, 1018 |
| Q-11 | 4 | 10 | 836, 1201, 1342, 1396 |
| Q-12 | 3 | 5 | 824, 1110, 1193 |
| Q-13 | 3 | 9 | 832, 1236, 1416 |
| Q-14 | 3 | 5 | 827, 1117, 1209 |
| Q-15 | 3 | 5 | 822, 1078, 1143 |
| Q-16 | 3 | 4 | 821, 1043, 1114 |
| Q-17 | 4 | 7 | 833, 1203, 1278, 1386 |
| Q-18 | 3 | 3 | 844, 996, 1065 |
| Q-19 | 3 | 5 | 821, 1106, 1185 |
| Q-20 | 3 | 7 | 834, 1249, 1338 |

## Questions where run 1 and run 2 differ (for C4)

- S1: ['Q-01', 'Q-03', 'Q-17']
- S2: ['Q-14', 'Q-15', 'Q-17']
- S3: ['Q-08', 'Q-17']

## C1 table

| Question | Calls (your description) | Calls (vague) | Answer (yours) | Answer (vague) |
|---|---:|---:|---|---|
| Q-03 | 7 | 5 | ['lindenmoor', 5.3] ✓ | ['lindenmoor', 5.3] ✓ |
| Q-08 | 4 | 4 | ['brightwater', 72.46] ✓ | ['brightwater', 72.46] ✓ |
| Q-09 | 7 | 5 | ['millbrook', 0.6] ✓ | ['millbrook', 0.6] ✓ |
| Q-14 | 5 | 5 | ['ashgrove', 4.9] ✓ | ['ashgrove', 4.9] ✓ |
| Q-20 | 7 | 10 | ['ashgrove', 890.0] ✗ | ['ashgrove', 2993.0] ✓ |
