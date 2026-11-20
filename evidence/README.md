# Evidence Folder Guide

During final review, I grouped the existing logs, results and screenshots by
task to make them easier to find. I used Codex to assist with the moves and
Markdown links. File contents were checked with SHA-256 hashes after moving.

| Folder | Contents |
|---|---|
| [fault-tolerance-demo/](fault-tolerance-demo/) | HDFS health check and replication reports before failure, during recovery, after re-replication and after restart |
| [data-preparation/](data-preparation/) | HDFS upload-verification listings, rainfall profile and provenance checksum report |
| [m1/](m1/) | Bus corridor sample/full results, execution logs and YARN screenshot |
| [m2/](m2/) | Rainfall sample/full results, execution logs and YARN screenshot |
| [m3/](m3/) | Parking-pressure sample/full results, execution logs and YARN screenshot |
| [m4/](m4/) | Integrated rainfall-parking sample/full results, execution logs and YARN screenshot |
| [performance analysis/m1/](performance%20analysis/m1/) | M1 benchmark runs 1-3: outputs, logs, timings and YARN screenshots |
| [performance analysis/m2/](performance%20analysis/m2/) | M2 benchmark runs 1-3: outputs, logs, timings and YARN screenshots |
| [troubleshooting/](troubleshooting/) | Original NameNode/ResourceManager startup name-resolution error excerpt |
| [progress-update-1/](progress-update-1/) | Original debugging journal and the historical logs/screenshots it references |

## Historical Paths

Earlier Word screenshots, commands and saved logs show the file paths used
when the work was performed. The folders were organised afterward. Examples:

| Earlier path | Current path |
|---|---|
| evidence/hdfs-fsck.txt | evidence/fault-tolerance-demo/hdfs-fsck.txt |
| evidence/m1-output.txt | evidence/m1/m1-output.txt |
| evidence/m1-benchmark-run1-log.txt | evidence/performance analysis/m1/m1-benchmark-run1-log.txt |

These changes do not represent new experiments. Current Markdown references
use the organised paths. Search by filename to locate files shown in older
screenshots. The Progress Update 1 archive retains its original internal folders
so its historical links continue to work.

## Reflection Note

During final review, I organised the accumulated logs, results and screenshots
by task. This made it easier to locate supporting evidence and check links.
The reorganisation also showed why consistent filenames and folders are useful
from the start of a project.

## Provenance Records

The [provenance write-up](../data_provenance.md) records sources, periods, row
counts, field mappings and limitations. The
[local file manifest](../userfiles/metadata/manifest.json) records file hashes
and intended HDFS locations. The HDFS byte-comparison report is saved in
data-preparation/provenance-hdfs-verification.txt. These local hashes are not
claimed as verified against a lecturer-issued manifest.
