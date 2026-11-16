#!/bin/bash
# test_mtu.sh :: configuracion de 5 routers con MTUs en las tablas (v3_mtu).
# Demuestra: check_routes devuelve (next_hop, MTU) y el router no se cae al
# enviar; los paquetes todavia pasan enteros (aun no se fragmentan).
# Logs del escenario en logs/mtu/

pkill -f "router.py" 2>/dev/null
sleep 0.5

LOGDIR=logs/mtu
mkdir -p "$LOGDIR"

python3 -u router.py 127.0.0.1 8881 rutas/rutas_R1_v3_mtu.txt > "$LOGDIR/R1.log" 2>&1 &
python3 -u router.py 127.0.0.1 8882 rutas/rutas_R2_v3_mtu.txt > "$LOGDIR/R2.log" 2>&1 &
python3 -u router.py 127.0.0.1 8883 rutas/rutas_R3_v3_mtu.txt > "$LOGDIR/R3.log" 2>&1 &
python3 -u router.py 127.0.0.1 8884 rutas/rutas_R4_v3_mtu.txt > "$LOGDIR/R4.log" 2>&1 &
python3 -u router.py 127.0.0.1 8885 rutas/rutas_R5_v3_mtu.txt > "$LOGDIR/R5.log" 2>&1 &
sleep 1

# destino directo (R2) y destino lejano (R5, cadena completa)
python3 enviar.py 127.0.0.1 8882 "hola R2!" 127.0.0.1 8881
python3 enviar.py 127.0.0.1 8885 "hola R5!" 127.0.0.1 8881
sleep 2

echo "=== R1 ==="; cat "$LOGDIR/R1.log"
echo "=== R2 ==="; cat "$LOGDIR/R2.log"
echo "=== R3 ==="; cat "$LOGDIR/R3.log"
echo "=== R4 ==="; cat "$LOGDIR/R4.log"
echo "=== R5 ==="; cat "$LOGDIR/R5.log"

pkill -f "router.py" 2>/dev/null
