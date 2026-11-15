.PHONY: review test
review:
	npm run review
test:
	npm test
	npm run typecheck

visual-review:
	node pipeline/visual-review.mjs
