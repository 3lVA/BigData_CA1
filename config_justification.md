# Hadoop Cluster Configuration Justification
I adapted the Practical 2 setup for one NameNode, three DataNodes,
one ResourceManager, one NodeManager and one client.

## Container Settings
| Setting | What it does | Why I retained it | Effect of changing or removing it |
|---|---|---|---|
| `image: liuzheng1990/hadoop-spark-sp:latest` | Provides the software used to create each container. | It contains the Hadoop installation used in Practical 2. | A different image may require changes to installation paths and commands. |
| `user: root` | Runs container processes as the Linux administrator. | It matches the starter's permissions for accessing mounted files. | A different user may require changes to file ownership and permissions. |
| `HADOOP_HOME=/opt/hadoop` | Identifies the Hadoop installation directory. | It matches the image's installation path. | An incorrect path could prevent scripts from locating Hadoop components. |
| `HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop` | Identifies the configuration directory. | It matches where my XML files are mounted. | An incorrect path could cause Hadoop to load different settings. |
| `HADOOP_LOG_DIR=/opt/hadoop/logs` | Identifies the Hadoop log directory. | I retained the starter's location for service logs. | An incorrect or unwritable directory could prevent log files being written. |
| `HDFS_NAMENODE_USER=root` and `HDFS_DATANODE_USER=root` | Specify users for Hadoop helper scripts that consult these variables. | I retained them to match the container user. | Their effect depends on the helper used. The NameNode variable on YARN/client services is inherited from the starter. |

## Storage and Configuration Mounts
| Setting | What it does | Why I used it | Effect of changing or removing it |
|---|---|---|---|
| `./namenode_data:/opt/hadoop/data/name` | Stores NameNode metadata in a host folder. | Metadata survives container recreation. | Removing it ties metadata to the container's writable layer. |
| Separate `datanode1_data`, `datanode2_data` and `datanode3_data` mounts at `/opt/hadoop/data/data` | Give each DataNode persistent block storage. | Each node needs its own independent storage directory. | Removing the mounts reduces persistence. Sharing one directory could cause storage conflicts. |
| `core-site.xml` and `hdfs-site.xml` mounts | Supply the HDFS address, replication and storage settings. | Relevant services need consistent HDFS configuration. | Removing them uses the image's configuration, which may differ. |
| `yarn-site.xml` and `mapred-site.xml` mounts | Supply YARN and MapReduce settings to the ResourceManager, NodeManager and client. | These services need compatible settings for job submission and execution. | Inconsistent configuration could disrupt job execution. |
| `:ro` on configuration mounts | Makes mounted files read-only inside containers. | I manage configuration through the host files. | Removing it permits container processes to modify the mounted files. |
| `log4j.properties` mount | Configures timestamped INFO-level console logs. | The logs help diagnose startup and execution problems. | Removing it uses the image's logging configuration. |

The storage paths in `hdfs-site.xml` match the destinations of the
NameNode and DataNode mounts.

## Ports and Startup
| Setting | What it does | Why I used it | Effect of changing or removing it |
|---|---|---|---|
| `9870:9870` | Publishes the NameNode web interface. | I use it to inspect DataNodes and browse HDFS. | Removing it removes access through `localhost:9870`. |
| `8088:8088` | Publishes the ResourceManager web interface. | I use it to inspect YARN workers and application results. | Removing it removes access through `localhost:8088`. |
| NameNode initialization check | Formats storage when the `current` directory is absent. | It initializes fresh storage and reuses existing metadata on later starts. | Removing initialization could prevent a fresh NameNode from starting. |
| Foreground daemon commands using `exec` | Start the NameNode, DataNodes, ResourceManager and NodeManager as their containers' main processes. | Docker can track the running service and deliver stop signals to it. | Removing the overrides leaves startup behavior to the image's defaults. |

## Client Settings
| Setting | What it does | Why I used it | Effect of changing or removing it |
|---|---|---|---|
| `./userfiles:/home/user/` | Shares local CSVs and Python scripts with the client. | It lets me upload data and submit jobs using host files. | Changing it requires updating paths in my commands. |
| `working_dir: /home/user` | Sets the starting directory for client commands. | Scripts can be run using relative filenames. | Changing it may require absolute script paths. |
| `command: bash`, `tty: true`, `stdin_open: true` | Start a shell with terminal support and keep input open. | They keep the client available for interactive use and Hadoop commands. | Changing them may cause the shell to exit or affect interactive use. |

## HDFS Choices
| Setting | What it does | Why I used it | Effect of changing it |
|---|---|---|---|
| Three DataNodes with `dfs.replication=2` | Stores two replicas of each new block on separate DataNodes. | A third node provides somewhere to create a replacement replica during an outage. | With only two nodes, HDFS cannot restore two live replicas while one is stopped. Replication of 1 leaves no surviving copy if its holder fails. |
| `dfs.blocksize=4194304` | Sets the default block size for new files to 4 MiB. | Larger CSVs span multiple blocks whose placement I can inspect. | Increasing it generally produces fewer blocks for newly uploaded large files. |
| `fs.defaultFS=hdfs://namenode:8020` | Directs filesystem requests to the NameNode through its Docker service name. | Containers can reach HDFS without depending on a fixed IP address. | An incorrect address could prevent access or direct commands to another filesystem. |