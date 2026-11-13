#!/bin/bash
# test_malconfig.sh :: prueba del informe: R2 con la tabla mal configurada
# (los paquetes con destino 8883 vuelven hacia R1 en vez de ir a R3).
# Con TTL=10 el paquete rebota R1<->R2 unas ~5 veces y muere por TTL.
# Logs del escenario en logs/malconfig/

pkill -f "router.py" 2>/dev/null
sleep 0.5

LOGDIR=logs/malconfig
mkdir -p "$LOGDIR"

python3 -u router.py 127.0.0.1 8881 rutas/rutas_R1_v2.txt > "$LOGDIR/R1.log" 2>&1 &
python3 -u router.py 127.0.0.1 8882 rutas/rutas_R2_mal.txt > "$LOGDIR/R2.log" 2>&1 &
python3 -u router.py 127.0.0.1 8883 rutas/rutas_R3_v2.txt > "$LOGDIR/R3.log" 2>&1 &
sleep 1

# TTL=10: hay que dar ~5 saltos de ida y vuelta para consumirlos, asi que el
# paquete rebota varias veces antes de morir. TTL=255: rebota ~127 veces.
python3 enviar.py 127.0.0.1 8883 "tengo mala ruta" 127.0.0.1 8881 10
python3 enviar.py 127.0.0.1 8883 "muchos saltos" 127.0.0.1 8881 255
sleep 2

echo "=== R1 ==="; cat "$LOGDIR/R1.log"
echo "=== R2 ==="; cat "$LOGDIR/R2.log"
echo "=== R3 (nunca recibe nada) ==="; cat "$LOGDIR/R3.log"

pkill -f "router.py" 2>/dev/null
