.PHONY: vm-ssh vm-deploy vm-status vm-logs

vm-ssh:
	./vm/ssh.sh

vm-deploy:
	./vm/deploy.sh

vm-status:
	./vm/status.sh

vm-logs:
	./vm/logs.sh
