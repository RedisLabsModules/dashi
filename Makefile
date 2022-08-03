
define HELPTEXT
make start       # start containers
make stop        # stop and remove containers
make dump        # create dump.sql from db container
make restore     # cleanup admin db in db container and apply dump.sql dump to admin db
make build       # build containers but don't start
  SERVICE=name     # build service `name`
make clean       # remove containers
  ALL=1            # remove images too
make logs        # show logs
  SERVICE=name     # show logs of service `name`
make setup       # install prerequisites

endef

PROJECT=dashi
COMPOSE=docker-compose --env-file .env -p $(PROJECT)

SERVICES=db app gather pqadmin

start up:
	@$(COMPOSE) up -d

stop down:
	@$(COMPOSE) down --remove-orphans

build:
	@$(COMPOSE) build $(SERVICE)

clean:
	@$(COMPOSE) rm
dump:
	@$(COMPOSE) exec db pg_dump -h localhost -Uadmin -d admin --clean > dump.sql
restore:
	@$(COMPOSE) exec -T db psql -h localhost -Uadmin -d admin < dump.sql
ifeq ($(ALL),1)
	@docker rmi -f $(addprefix $(PROJECT)_,$(SERVICES))
endif

logs:
	@$(COMPOSE) logs -f $(SERVICE)

setup:
	@./sbin/setup

ifneq ($(HELPTEXT),)
ifneq ($(filter help,$(MAKECMDGOALS)),)
HELPFILE:=$(shell mktemp /tmp/make.help.XXXX)
endif
endif

help:
	$(file >$(HELPFILE),$(HELPTEXT))
	@echo
	@cat $(HELPFILE)
	@echo
	@-rm -f $(HELPFILE)

.PHONY: start up stop down build clean logs test setup help

.EXPORT_ALL_VARIABLES:
	CIRCLE_CI_TOKEN=${CIRCLE_CI_TOKEN}
	GITHUB_TOKEN=${GITHUB_TOKEN}
