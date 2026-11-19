.PHONY: review test
review:
	npm run review
test:
	npm test
	npm run typecheck
	$(or $(PYTHON),python) -m unittest discover -s tests -p 'test_alignment.py'

visual-review:
	node pipeline/visual-review.mjs

grounded-ping:
	node pipeline/grounded-ping.mjs
