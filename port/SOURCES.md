# port/ holds byte-identical copies. Source pins:
# cmail-engine: cmail@583cd62 stevejobless/{engine,models,db,config}.py + connectors/
# pmail-qp: pmail@8869a4a src/{privacy/types,kernel,evidence/merkle,authority/grantex}
# qpbot-vault: qpbot agentcom/vault/store.py (Fernet grant-scoped secret store)
# qpbot-dash: qpbot dashboard/static/index.html design shell (see dash/static/ATTRIBUTION.md)
# Rule: port first, edits happen in core//qp//dash/ copies only, never here.
