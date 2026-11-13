#!/bin/bash
# run_all_tests.sh :: regenera toda la evidencia de la actividad:
# corre los 9 escenarios de prueba en secuencia y deja los logs en logs/.
# Cada script es autonomo (levanta su red, envia, muestra resultados, limpia).

set -e
bash test_forwarding_v1.sh
bash test_forwarding_v2.sh
bash test_roundrobin_v3.sh
bash test_roundrobin_v4.sh
bash test_default.sh
bash test_ttl.sh
bash test_malconfig.sh
bash test_archivo_grande.sh      # delay 0.05: orden preservado
bash test_archivo_grande.sh 0    # delay 0: desorden de llegada y perdidas por TTL

echo ""
echo "Evidencia regenerada en logs/:"
ls logs/
