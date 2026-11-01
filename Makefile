.PHONY: test lint demo

test:
	python3 -m unittest discover -s tests

lint:
	python3 -m json.tool .claude/settings.json >/dev/null
	python3 -m json.tool evals/evals.json >/dev/null

demo:
	sh tests/demo.sh
