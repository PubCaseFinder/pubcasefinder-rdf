#!/bin/sh

graph=$1
file=$2

ISQL_EXEC="/opt/virtuoso-opensource/bin/isql 1111 dba dba exec"

GRAPH_NAME="https://pubcasefinder.dbcls.jp/rdf/${graph}"
echo ${GRAPH_NAME}
echo "log_enable(2,1); ld_dir_all('/rdf_data/latest/', '${file}', '${GRAPH_NAME}');"

$ISQL_EXEC="DELETE FROM DB.DBA.LOAD_LIST WHERE ll_graph ='${GRAPH_NAME}';"
$ISQL_EXEC="log_enable(2,1); SPARQL CLEAR GRAPH <${GRAPH_NAME}>;"
$ISQL_EXEC="log_enable(2,1); ld_dir_all('/rdf_data/latest', '${file}', '${GRAPH_NAME}');"
$ISQL_EXEC="rdf_loader_run();"
$ISQL_EXEC="checkpoint;"