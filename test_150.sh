#!/bin/bash
# test_150.sh :: prueba del informe 2: paquete de 150 bytes totales enviado
# varias veces desde R1 a R5 y luego desde R5 a R1, con IDs distintos.
# Observa la fragmentacion, la re-fragmentacion segun el camino, y cuantos
# paquetes logran re-ensamblarse con TTL 10.
# Logs del escenario en logs/150/

pkill -f "router.py" 2>/dev/null
sleep 0.5

LOGDIR=logs/150
mkdir -p "$LOGDIR"

python3 -u router.py 127.0.0.1 8881 rutas/rutas_R1_v3_mtu.txt > "$LOGDIR/R1.log" 2>&1 &
python3 -u router.py 127.0.0.1 8882 rutas/rutas_R2_v3_mtu.txt > "$LOGDIR/R2.log" 2>&1 &
python3 -u router.py 127.0.0.1 8883 rutas/rutas_R3_v3_mtu.txt > "$LOGDIR/R3.log" 2>&1 &
python3 -u router.py 127.0.0.1 8884 rutas/rutas_R4_v3_mtu.txt > "$LOGDIR/R4.log" 2>&1 &
python3 -u router.py 127.0.0.1 8885 rutas/rutas_R5_v3_mtu.txt > "$LOGDIR/R5.log" 2>&1 &
sleep 1

MENSAJE150=$(python3 -c "print('x' * 132)")

# tres envios R1 -> R5
python3 enviar.py 127.0.0.1 8885 "$MENSAJE150" 127.0.0.1 8881 10 401
python3 enviar.py 127.0.0.1 8885 "$MENSAJE150" 127.0.0.1 8881 10 402
python3 enviar.py 127.0.0.1 8885 "$MENSAJE150" 127.0.0.1 8881 10 403
sleep 2

# dos envios en la direccion inversa, R5 -> R1
python3 enviar.py 127.0.0.1 8881 "$MENSAJE150" 127.0.0.1 8885 10 404
python3 enviar.py 127.0.0.1 8881 "$MENSAJE150" 127.0.0.1 8885 10 405
sleep 3

echo "=== R1 (destino de los inversos) ==="; cat "$LOGDIR/R1.log"
echo "=== R2 ==="; cat "$LOGDIR/R2.log"
echo "=== R5 (destino de los ida) ==="; cat "$LOGDIR/R5.log"

pkill -f "router.py" 2>/dev/null
