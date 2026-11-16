#!/bin/bash
# test_paquete_chico.sh :: prueba del informe 1: paquete sin fragmentar (23
# bytes) enviado 4 veces de R1 a R5. Verifica que TTL y round-robin siguen
# funcionando igual con el nuevo header: R2 alterna 8883/8884 y no hay
# ningun print de fragmentacion.
# Logs del escenario en logs/paquete_chico/

pkill -f "router.py" 2>/dev/null
sleep 0.5

LOGDIR=logs/paquete_chico
mkdir -p "$LOGDIR"

python3 -u router.py 127.0.0.1 8881 rutas/rutas_R1_v3_mtu.txt > "$LOGDIR/R1.log" 2>&1 &
python3 -u router.py 127.0.0.1 8882 rutas/rutas_R2_v3_mtu.txt > "$LOGDIR/R2.log" 2>&1 &
python3 -u router.py 127.0.0.1 8883 rutas/rutas_R3_v3_mtu.txt > "$LOGDIR/R3.log" 2>&1 &
python3 -u router.py 127.0.0.1 8884 rutas/rutas_R4_v3_mtu.txt > "$LOGDIR/R4.log" 2>&1 &
python3 -u router.py 127.0.0.1 8885 rutas/rutas_R5_v3_mtu.txt > "$LOGDIR/R5.log" 2>&1 &
sleep 1

python3 enviar.py 127.0.0.1 8885 "hola!" 127.0.0.1 8881 10 301
python3 enviar.py 127.0.0.1 8885 "hola!" 127.0.0.1 8881 10 302
python3 enviar.py 127.0.0.1 8885 "hola!" 127.0.0.1 8881 10 303
python3 enviar.py 127.0.0.1 8885 "hola!" 127.0.0.1 8881 10 304
sleep 2

echo "=== R2 (alterna caminos, decae TTL) ==="; cat "$LOGDIR/R2.log"
echo "=== R5 (imprime 4 veces) ==="; cat "$LOGDIR/R5.log"

pkill -f "router.py" 2>/dev/null
