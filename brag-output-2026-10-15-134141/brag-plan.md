# Brag plan: Hotel Management AI Agent (v3, every action)

Extends v2 (`brag-output-2026-10-15-093345`) from 4 agent actions to all 15 shown in `demo/`.
Same angle, look and hook: "Check a guest in by just saying so." 1920x1080, 30fps, 72.2s.

## Sources
- Agent replies are the real wording from the demo screenshots (some long replies trimmed to their first sentences).
- Tool chips use the real tool names from `hotel_agent.ipynb`.
- **Privacy:** a delete-confirmation screenshot shows a real name, phone and email. That record is swapped for the demo's
  fictional "John Smith, room 150, customer #4". The PDF path is shortened to `customer_list.pdf`. All other guests are demo test data
  (Jane Smith, Amara Perera @example.com, Test User, Zzz Nobody).

## Storyboard (each chat scene shows "NN / 15" + action name)
| # | Time | Action | Demo shot | Caption |
|---|---|---|---|---|
| - | 0.0-2.4 | Hook: the request types itself | - | Check a guest in / by just saying so. |
| 01 | 2.4-8.4 | Add a guest | 01 | Asks for what's missing. `save_customer()` |
| 02 | 8.4-12.4 | View by ID | 02 | Pull up any guest by ID. `view_customer()` |
| 03 | 12.4-16.8 | Find by name, duplicates | 03, 04, 20 | Same name? It asks which. |
| 04 | 16.8-20.6 | Not found | 05 | No match, no make-believe. |
| 05 | 20.6-24.4 | Update | 06 | Move a guest in one line. `update_customer()` |
| 06 | 24.4-28.4 | ID change refused | 07 | IDs stay put. |
| 07 | 28.4-32.2 | Bad phone rejected | 08 | Bad data gets a polite no. |
| 08 | 32.2-36.4 | Bad dates rejected | 09 | Time travel not supported. |
| 09 | 36.4-41.4 | Delete confirmed | 10 | Gone, once you say yes. `delete_customer()` |
| 10 | 41.4-46.4 | Delete cancelled | 11, 12 | No delete without a yes. |
| 11 | 46.4-50.8 | List all (table) | 16 | The whole register. `list_customers()` |
| 12 | 50.8-55.8 | Search by date, found + none | 17, 18 | Who's arriving today? `search_by_check_in_date()` |
| 13 | 55.8-59.8 | Export PDF | 19 | Print-ready, on request. `export_customers_pdf()` |
| 14 | 59.8-64.0 | Persistence after restart | 15 | Restart it. Still there. |
| 15 | 64.0-68.6 | Off-topic: price + payment | 13, 14 | Won't quote you a price. |
| - | 68.6-72.2 | Outro: title, feature chips, stack, run command | - | |

Transitions: the chat window stays put; old messages and caption fade out, then new ones fade in. Long replies scroll inside the panel like Gradio does.

## Sound
Same A-minor/C palette at 120 bpm, one chord per scene cycling Am-F-C-G, a Cadd9 lift for the outro. Message pops are generated from the chat timeline (user E5, agent A5, a soft C5 for "Kernel restarted"), all under the music with one shared short reverb.
