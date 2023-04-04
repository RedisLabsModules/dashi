
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
  FOLLOW=1         # follow log
make setup       # install prerequisites

endef

PROJECT=dashi
COMPOSE=docker-compose -p $(PROJECT)

SERVICES=db app sidecar adminer

start up:
	@$(COMPOSE) up -d

stop down: dump
	@$(COMPOSE) down --remove-orphans

build:
	@$(COMPOSE) build $(SERVICE)

clean:
	@$(COMPOSE) rm
ifeq ($(ALL),1)
	@docker rmi -f $(addprefix $(PROJECT)_,$(SERVICES))
endif

dump:
	@$(COMPOSE) exec db pg_dump -h localhost -Uadmin -d admin --clean > db/dump.sql

restore:
	@$(COMPOSE) exec -T db psql -h localhost -Uadmin -d admin < db/dump.sql

ifeq ($(FOLLOW),1)
LOG_FOLLOW=-f
endif

logs:
	@$(COMPOSE) logs $(LOG_FOLLOW) $(SERVICE)

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
	GH_TOKEN=${GH_TOKEN}
