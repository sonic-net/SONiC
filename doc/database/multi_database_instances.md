# Support Multiple user-defined redis database instances

## Current implementation

- Single redis database instance for all database tables
- All database configuration files (supervisord.conf, redis.conf, redis.sock. redis.pid and etc.) are generated at compilation. They cannot be modified at runtime
- ![](/home/dzhang/SONiC_Doc/SONiC/doc/database/img/current_DB.png)

1. DUT try to load a new images
   - [ ] if configuration at /etc/sonic/ exists, copy /etc/sonic/ to /host/old_config
2. rc.local service
   - [ ] if /host/old_config/ exists, copy /host/old_config/ to /etc/sonic/
   - [ ] if no folder /host/old_config/, copy some default xmls and etc.
3. database service
   - [ ] database.sh start and docker start according to the configuration
   - [ ] check if database is running
4. updategraph service
   - [ ] depends on rc.local and database
   - [ ] restore /etc/sonic/old_config to /etc/sonic/, if any
   - [ ] if no folder /etc/sonic/old_config/, generate config_db.json based on xml and etc.

## New Design

- New Schema used in config_db.json

- ![](/home/dzhang/SONiC_Doc/SONiC/doc/database/img/database.sample.png)
- DO NOT change the original single redis database instance implementation
  - If we don't have any DATABASE configuration in config_db.json, the default redis database instance is there and behaves the same as what it does today
  - If we have some DATABASE configuration in config_db.json,  besides the default redis database instance, we create these extra database instances, later the users can choose which database instances they want to use according to their configuration in config_db.json (this is the next plan after this, database table related).

- Create required redis database instances based on configuration in config_db.json
- All database related configuration(supervisord.conf, redis.conf, redis.sock, redis.pid and etc.) should be generated at runtime
- ![](/home/dzhang/SONiC_Doc/SONiC/doc/database/img/newDesign.png)

1. DUT try to load a new images (no changes)
   - [ ] if configuration at /etc/sonic/ exists, copy /etc/sonic/ to /host/old_config as usual
2. rc.local service (no changes)
   - [ ] if /host/old_config/ exists, copy /host/old_config/ to /etc/sonic/ as usual
   - [ ] if no folder /host/old_config/, copy some default xmls and etc. as usual
3. **database service**
   - [ ] **make database service depends on rc.local service since database needs to access old_config/config_db.json to get DATABASE configuration earlier**
   - [ ] **database.sh start**
     - [ ] **access and copy /etc/sonic/old_config/config_db.json earlier into /etc/sonic/**
     - [ ] **If there is no old_config folder, we take it as no extra DATABASE requirement  and create a empty "{}" config_db.json to pass.**
     - [ ] **generate corresponding runtime ping/PONG check script as well to check if database instances are running later**
   - [ ] **docker ENTRYPOINT : docker_init.sh**
     - [ ] **at this point, we know the DATABASE configuration in config_db.json**
     - [ ] **generate supervisord.conf and all redis.conf before database docker start**
     - [ ] **exec supervisord**
   - [ ] **supervisord**
     - [ ] **start database programs after all runtime configuration are generated**
   - [ ] **check if database instances are running via ping/PONG check script**
4. updategraph service (no changes)
   - [ ] depends on rc.local and database
   - [ ] restore /etc/sonic/old_config to /etc/sonic/, if any
   - [ ] if no folder /etc/sonic/old_config/, generate config_db.json based on xml and etc.
   - [ ] config_db.json file, if any, created via database service will be overwritten here