
CLIENT_IDS=1 2 3 4 5
#CLIENT_IDS=1 2

.PHONY: clean

clean:
	@for id in $(CLIENT_IDS); do \
		PORT=$$(($$id * 1234)); \
		PID=$$(lsof -t -i :$$PORT); \
		if [ -n "$$PID" ]; then \
			echo "Killing client $$id with PID $$PID (port $$PORT)"; \
			kill $$PID; \
		else \
			echo "No client process found on port $$PORT"; \
		fi \
	done