# Done tasks (DO not perform any of these already done)
- [x] Refactor main.py to take helm chart as arguments
- [x] Docs upto date with usage instruction

# Task
- Can you create two mutually exclusive flag `hide-resource` and `resource`
- For flag `hide-resource`
    - it is multivalue field of type string
    - User can provide multiple resources comma seperated 
    - When provided, in final output, helm-impact should display impact of all resources except those provided
    as hide resources

- For flag `resource`
    - it is multivalue field of type string
    - User can provide multiple resources comma seperated 
    - When provided, in final output, helm-impact should display impact of all resources for those provided
    as resources

IMPORTANT: Do not cram code in single file. You are expert python developer which write idomatic python code. Refactor the code if you have to. Prioritze simplicity first though