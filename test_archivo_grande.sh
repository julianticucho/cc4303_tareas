#!/bin/bash
# test_archivo_grande.sh :: prueba del informe: envio de un archivo de varias
# lineas con prueba_router.py por la red de 5 routers (v3), y comparacion del
# orden de llegada en R5 contra el orden de envio.
# Logs del escenario en logs/archivo_grande_delay<delay>/, asi cada variante
# deja su evidencia en una carpeta distinta y no se pisan
# delay: 1er argumento opcional (default 0.05). Con delay 0 se observan
# desorden de llegada y perdidas por TTL en la red de 5 routers.

pkill -f "router.py" 2>/dev/null
sleep 0.5

LOGDIR=logs/archivo_grande_delay${1:-0.05}
mkdir -p "$LOGDIR"

DELAY=${1:-0.05}

python3 -u router.py 127.0.0.1 8881 rutas/rutas_R1_v3.txt > "$LOGDIR/R1.log" 2>&1 &
python3 -u router.py 127.0.0.1 8882 rutas/rutas_R2_v3.txt > "$LOGDIR/R2.log" 2>&1 &
python3 -u router.py 127.0.0.1 8883 rutas/rutas_R3_v3.txt > "$LOGDIR/R3.log" 2>&1 &
python3 -u router.py 127.0.0.1 8884 rutas/rutas_R4_v3.txt > "$LOGDIR/R4.log" 2>&1 &
python3 -u router.py 127.0.0.1 8885 rutas/rutas_R5_v3.txt > "$LOGDIR/R5.log" 2>&1 &
sleep 1

# archivo de 50 lineas: linea 1 ... linea 50
seq 1 50 | sed 's/^/linea /' > archivo_grande.txt

# delay 0.05s: deja respiro para que los caminos distintos (por R3 o por R4)
# puedan invertir el orden de llegada
python3 prueba_router.py "127.0.0.1;8885;10" 127.0.0.1 8881 "$DELAY" < archivo_grande.txt
sleep 3

echo "=== orden de envio ==="; cat archivo_grande.txt
echo "=== orden de llegada en R5 ==="; cat "$LOGDIR/R5.log"

pkill -f "router.py" 2>/dev/null
