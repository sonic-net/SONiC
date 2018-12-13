# Support Multiple user-defined redis database instances

## Motivation

Today SONiC only has one redis database instance created and all the databases use this unique database instance, like APPL_DB, ASIC_DB, CONF_DB and so on.  We found when there are huge writes operations during a short time period (like huge routes created), this only database instance is very  busy. We tried to create two database instances and separate the huge write into two database instances. The test result shows the performance (time) improved 20-30%. Also creating multiple database instances help us to separate the databases based on their operation frequency or their role in the whole SONiC system, for example, like state database and loglevel database are not key features, we can avoid them affecting read and write APPL_DB or ASIC_DB  via multiple database instances.  

## Current implementation

- Single Redis database instance for all databases
- All database configuration files (supervisord.conf, redis.conf, redis.sock. redis.pid and etc.) are generated at compilation. They cannot be modified at runtime
- ![](./img/current_DB.png)

1. DUT try to load a new images
   - [x] if configuration at /etc/sonic/ exists, copy /etc/sonic/ to /host/old_config
2. rc.local service
   - [x] if /host/old_config/ exists, copy /host/old_config/ to /etc/sonic/
   - [x] if no folder /host/old_config/, copy some default xmls and etc.
3. database service
   - [x] database.sh start and docker start according to the configuration
   - [x] check if database is running
4. updategraph service
   - [x] depends on rc.local and database
   - [x] restore /etc/sonic/old_config to /etc/sonic/, if any
   - [x] if no folder /etc/sonic/old_config/, generate config_db.json based on xml and etc.

## New Design of Database Startup 

- We introduce a new configuration file at /etc/sonic/database_config.json

- This file contains how may database instances and on each instance what the configuration is

  ```json
  {
      "DATABASE": {
          "redis_ins_001":{
              "port": 6380,
              "databases" : ["LOGLEVEL_DB","SYSMON_DB","COUNTERS_DB"]
          },
          "redis_ins_002":{
              "port": 6381,
              "databases" : ["APPL_DB","ASIC_DB", "CONFIG_DB"]
          },
          "redis_ins_003":{
              "port": 6382,
              "databases" : ["STATE_DB","FLEX_COUNTER_DB","PFC_WD_DB"]
          }
      }
  }
  ```

- DO NOT change the original single redis database instance implementation
  - [x] If we don't have any DATABASE configuration in database_config.json, the default redis database instance is there and behaves the same as what it does today
  - [x] If we have some DATABASE configuration in database_config.json,  besides the default redis database instance, we create these extra database instances, later the users can choose which database instances they want to use according to their configuration in database_config.json

- All database related configuration(supervisord.conf, redis.conf, redis.sock, redis.pid and etc.) should be generated at runtime

- ![](./img/newDesign.png)

1. DUT try to load a new images (no changes)
   - [x] if configuration at /etc/sonic/ exists, copy /etc/sonic/ to /host/old_config as usual
2. rc.local service (no changes)
   - [x] if /host/old_config/ exists, copy /host/old_config/ to /etc/sonic/ as usual
   - [x] if no folder /host/old_config/, copy some default xmls and etc. as usual
3. **database service**
   - [x] **make database service depends on rc.local service since database needs to access old_config/config_db.json to get DATABASE configuration earlier**
   - [x] **database.sh start**
     - [x] **access and copy /etc/sonic/old_config/database_config.json into /etc/sonic/**
     - [x] **If there is no old_config folder or database_config.json file, we take it as no extra DATABASE requirement  and create a empty "{}" database_config.json.**
     - [x] **generate corresponding runtime ping/PONG check script as well to check if database instances are running later**
   - [x] **docker ENTRYPOINT : docker_init.sh**
     - [x] **at this point, we know the DATABASE configuration in database_config.json**
     - [x] **generate supervisord.conf and all redis.conf before database docker start**
     - [x] **exec supervisord**
   - [x] **supervisord**
     - [x] **start database programs after all runtime configuration are generated**
   - [x] **check if database instances are running via ping/PONG check script**
4. updategraph service (no changes)
   - [x] depends on rc.local and database
   - [x] restore /etc/sonic/old_config to /etc/sonic/, if any
   - [x] if no folder /etc/sonic/old_config/, generate config_db.json based on xml and etc.

## Potential Redis Cluster Solution

Could we use cluster feature on single instance to split the databases across different nodes instead of creating multiple single redis instances mentioned in this Design Document ?

**What is the goals of Redis Cluster?** 

Redis Cluster is a distributed implementation of Redis with the following goals, in order of importance in the design:

1. High performance and linear scalability up to 1000 nodes. There are no proxies, asynchronous replication is used, and no merge operations are performed on values.
2. Acceptable degree of write safety: the system tries (in a best-effort way) to retain all the writes originating from clients connected with the majority of the master nodes. Usually there are small windows where acknowledged writes can be lost. Windows to lose acknowledged writes are larger when clients are in a minority partition.
3. Availability: Redis Cluster is able to survive partitions where the majority of the master nodes are reachable and there is at least one reachable slave for every master node that is no longer reachable. Moreover using replicas migration, masters no longer replicated by any slave will receive one from a master which is covered by multiple slaves.

**Clients and Servers roles in the Redis Cluster protocol**
​        In Redis Cluster nodes are responsible for holding the data, and taking the state of the cluster, including mapping keys to the right nodes. Cluster nodes are also able to auto-discover other nodes, detect non-working nodes, and promote slave nodes to master when needed in order to continue to operate when a failure occurs.

​        To perform their tasks all the cluster nodes are connected using a **TCP bus** and a binary protocol, called the Redis Cluster Bus. Every node is connected to every other node in the cluster using the cluster bus. Nodes use a gossip protocol to propagate information about the cluster in order to discover new nodes, to send ping packets to make sure all the other nodes are working properly, and to send cluster messages needed to signal specific conditions. The cluster bus is also used in order to propagate Pub/Sub messages across the cluster and to orchestrate manual failovers when requested by users (manual failovers are failovers which are not initiated by the Redis Cluster failure detector, but by the system administrator directly).

![](/home/dzhang/SONiC_Doc/SONiC/doc/database/img/redis_cluster.jpg)

**Redis Cluster Main Components:**

***KEYs distribution model :***

​	HASH_SLOT = CRC16(key) mod 16384

**Cluster nodes attributes:**

​	Every node has a unique name in the cluster. The node name is the hex representation of a 160 bit random number, obtained the first time a node is started (usually using /dev/urandom).

​	Every node maintains the following information about other nodes that it is aware of in the cluster: The node ID, IP and port of the node, a set of flags, what is the master of the node if it is flagged as slave, last time the node was pinged and the last time the pong was received, the current configuration epoch of the node (explained later in this specification), the link state and finally the set of hash slots served.

```shell
`$ redis-cli cluster nodes
d1861060fe6a534d42d8a19aeb36600e18785e04 127.0.0.1:6379 myself - 0 1318428930 1 connected 0-1364
3886e65cc906bfd9b1f7e7bde468726a052d1dae 127.0.0.1:6380 master - 1318428930 1318428931 2 connected 1365-2729
d289c575dcbc4bdd2931585fd4339089e461a27d 127.0.0.1:6381 master - 1318428931 1318428931 3 connected 2730-4095`
```

**The Cluster bus:**
​	Every Redis Cluster node has an additional TCP port for receiving incoming connections from other Redis Cluster nodes. This port is at a fixed offset from the normal TCP port used to receive incoming connections from clients. To obtain the Redis Cluster port, 10000 should be added to the normal commands port. For example, if a Redis node is listening for client connections on port 6379, the Cluster bus port 16379 will also be opened.

**The Fact we cannot use redis cluster to distribute all databases across different nodes.**

1. TCP + PORT must be used in cluster, we cannot use socket.
2. Mapping KEY to hash slot is not decided by us. It is hard to generate the same hash value/slot for all the different KEYs in one database in order to distribute the databases across nodes.
3. Also, in cluster mode, each redis instance only has one database, we cannot apply two or more databases on the same redis instance.
4. For warm reboot, we cannot restore the data form current saved backup file to start the redis cluster mode unless we don't want to support it.

**So I don't think redis cluster is a good way to solve the problem of distributing databases into multiple redis instances in SONiC.**

## New Design of C++ Interface :  DBConnector()

Today there are two APIs to create DBConnector object which depends on socket OR port number as input:

```c++
DBConnector(int dbId, const std::string &hostname, int port, unsigned int timeout);
DBConnector(int dbId, const std::string &unixPath, unsigned int timeout);
```

The new design introduce a new class DBConnectorDB which is used to read database_config.json file and store the database configuration information once. We declare a static member of DBConnectorDB class in original DBConnector which make sure it is only read the configuration file once.

Also we introduce a new API to create DBConnector object without socket/port parameter. The socket/port will be decided via lookup using DBConnectorDB static member.

dbconnector.h

```c++
class DBConnectorDB
{
public:
    const std::string DB_CONFIG_FILE = "/etc/sonic/database_config.json";
    const std::string DB_MAPPING_FILE = "/usr/local/lib/python2.7/dist-packages/swsssdk/config/database.json";
    const std::string DB_DEFAULT_SOCK = "/var/run/redis/redis.sock";
    const std::string DB_DEFAULT_SOCK_PATH = "/var/run/redis/";
    const int DB_DEFAULT_PORT = 6379;
    DBConnectorDB();
    std::string getSock(int dbId);
    int getPort(int dbId);

private:
    std::unordered_map<int, std::pair<std::string, int>> db2sockport;
    std::unordered_map<std::string, int> dbstr2num;
};

class DBConnector
{
public:
    static constexpr const char *DEFAULT_UNIXSOCKET = "/var/run/redis/redis.sock";
    DBConnector(int dbId, const std::string &hostname, int port, unsigned int timeout);
    DBConnector(int dbId, const std::string &unixPath, unsigned int timeout);
    DBConnector(int dbId, unsigned int timeout);
    ~DBConnector();
    redisContext *getContext();
    int getDbId();
    static void select(DBConnector *db);
    DBConnector *newConnector(unsigned int timeout);
private:
    redisContext *m_conn;
    int m_dbId;
    static DBConnectorDB dbconndb;
};
```

The last step is to replace the places where using the old DBConnector() with the new DBConnector() API.

dbconnector.cpp

```c++
//swss::DBConnector db(ASIC_DB, DBConnector::DEFAULT_UNIXSOCKET, 0);
swss::DBConnector db(ASIC_DB, 0);

DBConnector::DBConnector(int dbId, unsigned int timeout) :
    m_dbId(dbId)
{
    struct timeval tv = {0, (suseconds_t)timeout * 1000};

    if (timeout)
        m_conn = redisConnectUnixWithTimeout(dbconndb.getSock(dbId).c_str(), tv);
    else
        m_conn = redisConnectUnix(dbconndb.getSock(dbId).c_str());

    if (m_conn->err)
        throw system_error(make_error_code(errc::address_not_available),
                           "Unable to connect to redis (unixs-socket)");

    select(this);
}
```

## New Design of Python Interface: DBConnector()

Python DBConnector() is auto generated via C++ Codes. No need to change.

## New Design of Python Interface: SonicV2Connector() 

Today the usage is to accept parameter in SonicV2Connector() init and then call connect() to create connection to default redis instance.

```python
 self.appdb = SonicV2Connector(host="127.0.0.1")
 self.appdb.connect(self.appdb.APPL_DB)
```

We first add the codes/API into \_\_init\_\_.py in swsssdk package to read database_config.json file and store the database configuration information at the very beginning. Later when importing swsssdk package, other python modules can use this information which is similar to existing  _connector_map.

\_\_init\_\_.py

```python
DEFAULT_REDIS_SOCK_PATH = "/var/run/redis/"
DEFAULT_REDIS_SOCK = DEFAULT_REDIS_SOCK_PATH + "redis.sock"
DEFAULT_REDIS_PORT = 6379

def _parse_db_inst_mapping():
    global _dbnm2port
    global _dbnm2sock
    global _db_inst_map
    if 'DATABASE' in _db_inst_map:
        for item in _db_inst_map["DATABASE"]:
            inst = item
            _port = _db_inst_map"DATABASE"["port"]
            for db in _db_inst_map"DATABASE"["databases"]:
                _sock = DEFAULT_REDIS_SOCK_PATH + inst + ".sock"
                _dbnm2port[db] = _port
                _dbnm2sock[db] = _sock

def _get_redis_sock(db_name):
    if db_name in _dbnm2sock:
        return _dbnm2sock[db_name]
    else:
        return DEFAULT_REDIS_SOCK

def _get_redis_port(db_name):
    if db_name in _dbnm2port:
        return _dbnm2port[db_name]
    else:
        return DEFAULT_REDIS_PORT

_dbnm2port = {}
_dbnm2sock = {}
_db_inst_map = {}
_connector_map = {}
_load_connector_map()
_parse_db_inst_mapping()
```

Then when connecting database in the connect() function in interface.py , we choose the database instance based on database id instead of using the default redis instance.

interface.py

```python
def _onetime_connect(self, db_name):
    """
    Connect to named database.
    self.redis_kwargs = {'unix_socket_path': _get_redis_sock(db_name)}
    self.redis_kwargs = {'host': "127.0.0.1", 'port': _get_redis_port(db_name)}
    """
    db_id = self.get_dbid(db_name)
    if db_id is None:
        raise ValueError("No database ID configured for '{}'".format(db_name))

    self.redis_kwargs = {'host': "127.0.0.1", 'port': _get_redis_port(db_name)}

    client = redis.StrictRedis(db=self.db_map[db_name]['db'], **self.redis_kwargs)

    # Enable the notification mechanism for keyspace events in Redis
    client.config_set('notify-keyspace-events', self.KEYSPACE_EVENTS)
    self.redis_clients[db_name] = client
```
For this part, the current code where uses parameters in SonicV2Connector(port/socket) is not necessary anymore. We need to remove them though there is no effect for now.

```python
 # self.appdb = SonicV2Connector(host="127.0.0.1")
 self.appdb = SonicV2Connector()
 self.appdb.connect(self.appdb.APPL_DB)
```

## Golang:  initialize DB connection Design

Today we create all database connection at init time using default redis instance and later we just use it.

db_client.go

```go
// Client package prepare redis clients to all DBs automatically
func init() {
    db_init()
    for dbName, dbn := range spb.Target_value {
        if dbName != "OTHERS" {
            // DB connector for direct redis operation
            var redisDb *redis.Client
            redisDb = redis.NewClient(&redis.Options{
                        Network:     "unix",
                        Addr:        Default_REDIS_UNIXSOCKET,
                        Password:    "", // no password set
                        DB:          int(dbn),
                        DialTimeout: 0,
                })
                Target2RedisDb[dbName] = redisDb
        }
    }
} 
```

In the new Design, similar to C++ changes, in the init time , we first add function to read database_config.json file and store the database information.   Later we use the API to get the information when we want to use it.

db_client.go

```go
const (
        // indentString represents the default indentation string used for
        // JSON. Two spaces are used here.
        indentString                 string = "  "
        Default_REDIS_UNIXSOCKET     string = "/var/run/redis/redis.sock"
        Default_REDIS_LOCAL_TCP_PORT string = "localhost:6379"
        Default_REDIS_DATABASE_CONF_FILE string = "/etc/sonic/database_config.json"
)

func GetRedisSock(db_name string)(string) {
    v, ok := DbName2RedisSock[db_name]
    if ok {
        log.V(1).Infof("Created %s socket on %s", v, db_name)
        return v
    }
    log.V(1).Infof("Created %s socket on %s", Default_REDIS_UNIXSOCKET,db_name)
    return Default_REDIS_UNIXSOCKET
}

func GetRedisPort(db_name string)(string) {
    v, ok := DbName2RedisPort[db_name]
    if ok {
        log.V(1).Infof("Created %s port on %s", v, db_name)
        return v
    }
    log.V(1).Infof("Created %s port on %s", Default_REDIS_LOCAL_TCP_PORT, db_name)
    return Default_REDIS_LOCAL_TCP_PORT
}

func db_init() {
    data, err := io.ReadFile(Default_REDIS_DATABASE_CONF_FILE)
    if err != nil {
        fmt.Println(err)
    }
    var dat map[string]interface{}
    err = json.Unmarshal([]byte(data), &dat)
    if err != nil {
        fmt.Println(err)
    }
    if v, ok := dat["DATABASE"]; ok {
       insts := v.(map[string]interface{})
       for instName,val := range insts {
           paras := val.(map[string]interface{})
           port := paras["port"].(float64)
           dbnames := paras["databases"].([]interface{})
           for i := range dbnames {
               DbName2RedisSock[dbnames[i].(string)] = "/var/run/redis/" + instName + ".sock"
               str_port := fmt.Sprintf("%.0f", port)
               DbName2RedisPort[dbnames[i].(string)] = "localhost:" + str_port
           }
       }
    }
}
```

The last step is to replace the hard coded socket/port with the API

db_client.go

```go
// Client package prepare redis clients to all DBs automatically
func init() {
    db_init()
    for dbName, dbn := range spb.Target_value {
        if dbName != "OTHERS" {
            // DB connector for direct redis operation
            var redisDb *redis.Client
            redisDb = redis.NewClient(&redis.Options{
                        Network:     "unix",
                        Addr:  GetRedisSock(dbName),//Default_REDIS_UNIXSOCKET,
                        Password:    "", // no password set
                        DB:          int(dbn),
                        DialTimeout: 0,
                })
                Target2RedisDb[dbName] = redisDb
        }
    }
}
```

## New Design of Script:   insert -p/-s while using redis-cli cmd

For the script, today we just use the default redis instance and there is no -p/-s option.

The scripts is used in shell, python, c and c++ system call, we need to change all these places.

we just used the python API we added earlier in \_\_init\_\_.py in swsssdk package to achieve this .  

Shell e.g.:

```shell
arp_to_host_flag=$(echo $(redis-cli -n 4 hget "ARP|arp2host" enable) | tr [a-z][A-Z])
```

```shell
 arp_to_host_flag=$(echo $(redis-cli -p `python -c 'from swsssdk import _get_redis_port; print _get_redis_port("CONFIG_DB")'` -n 4 hget "ARP|arp2host" enable) | tr [a-z][A-Z])
```

python e.g.:

```python
proc = Popen("docker exec -i database redis-cli --raw -n 2 KEYS *CRM:ACL_TABLE_STATS*", stdout=PIPE, stderr=PIPE, shell=True
```

```python
from swsssdk import _get_redis_port_

_proc = Popen("docker exec -i database redis-cli -p " + str(_get_redis_port("COUNTERS_DB")) + " --raw -n 2 KEYS *CRM:ACL_TABLE_STATS*    ", stdout=PIPE, stderr=PIPE, shell=True
```

C/C++ e.g.:

```c++
//string redis_cmd_db = "redis-cli -p -n ";
string redis_cmd_db = "redis-cli -p `python -c \"from swsssdk import _get_redis_port; print _get_redis_port(\\\"CONFIG_DB\\\")\"` -n ";

redis_cmd_db += std::to_string(CONFIG_DB) + " ";

redis_cmd = redis_cmd_db + " KEYS " + redis_cmd_keys;
redis_cmd += " | xargs -n 1  -I %   sh -c 'echo \"%\"; ";
redis_cmd += redis_cmd_db + "hgetall \"%\" | paste -d '='  - - | sed  's/^/$/'; echo'";

EXEC_WITH_ERROR_THROW(cmd, res);
```



## Platform VS 

platform vs is not changed at this moment. For the vs tests, they are still using one database instance since platform vs database configuration is different from that at database-docker. For vs test, it is enough to use on database instance.

## Testing 

We apply this changes on our local switches at labs. All the database are assigned to different database instances based on configuration.  So far, for the real traffic things looks great, all the tables , entries work properly. We will keep doing tests and running with traffic and see.