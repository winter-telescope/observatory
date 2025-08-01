```mermaid
---
State Machine
---
stateDiagram-v2
  direction LR
  classDef s_default fill:white,color:black
  classDef s_inactive fill:white,color:black
  classDef s_parallel color:black,fill:white
  classDef s_active color:red,fill:darksalmon
  classDef s_previous color:blue,fill:azure
  
  state "asleep" as asleep
  Class asleep s_active
  state "hanging out" as hanging out
  Class hanging out s_default
  state "hungry" as hungry
  Class hungry s_default
  state "sweaty" as sweaty
  Class sweaty s_default
  state "saving the world" as saving the world
  Class saving the world s_default
  
  asleep --> hanging out: wake_up
  asleep --> saving the world: distress_call
  asleep --> asleep: nap
  hanging out --> hungry: work_out
  hanging out --> saving the world: distress_call
  hanging out --> asleep: nap
  hungry --> hanging out: eat
  hungry --> saving the world: distress_call
  hungry --> asleep: nap
  sweaty --> saving the world: distress_call
  sweaty --> asleep: clean_up | nap
  sweaty --> hanging out: clean_up
  saving the world --> saving the world: distress_call
  saving the world --> sweaty: complete_mission
  saving the world --> asleep: nap
  [*] --> asleep
  ```