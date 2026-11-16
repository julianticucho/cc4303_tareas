#!/bin/bash
# run_all_tests.sh :: regenera toda la evidencia de la actividad de
# fragmentacion: corre los tests unitarios y los 6 escenarios de red en
# secuencia, y deja los logs en logs/<escenario>/

set -e
python3 test_parse.py
python3 test_routes.py
python3 test_fragment.py
python3 test_reassemble.py
bash test_mtu.sh
bash test_fragmentacion.sh
bash test_reensamblado.sh
bash test_fragmentos_manual.sh
bash test_paquete_chico.sh
bash test_150.sh

echo ""
echo "Evidencia regenerada en logs/:"
ls logs/
