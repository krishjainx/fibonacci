```bash
docker rm -v -f $(docker ps -qa) ; make clean ; make build ; make run 
```
