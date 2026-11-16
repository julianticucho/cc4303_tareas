#!/bin/bash
# test_fragmentacion.sh :: red de 5 routers con MTU y fragmentacion activa.
# Envia un paquete chico (no se fragmenta) y uno de 150 bytes (se fragmenta
# en R1 y se re-fragmenta en R2 segun el camino que elija el round-robin).
# Logs del escenario en logs/fragmentacion/

pkill -f "router.py" 2>/dev/null
sleep 0.5

LOGDIR=logs/fragmentacion
mkdir -p "$LOGDIR"

python3 -u router.py 127.0.0.1 8881 rutas/rutas_R1_v3_mtu.txt > "$LOGDIR/R1.log" 2>&1 &
python3 -u router.py 127.0.0.1 8882 rutas/rutas_R2_v3_mtu.txt > "$LOGDIR/R2.log" 2>&1 &
python3 -u router.py 127.0.0.1 8883 rutas/rutas_R3_v3_mtu.txt > "$LOGDIR/R3.log" 2>&1 &
python3 -u router.py 127.0.0.1 8884 rutas/rutas_R4_v3_mtu.txt > "$LOGDIR/R4.log" 2>&1 &
python3 -u router.py 127.0.0.1 8885 rutas/rutas_R5_v3_mtu.txt > "$LOGDIR/R5.log" 2>&1 &
sleep 1

# paquete chico: cabe en todos los enlaces, pasa entero
python3 enviar.py 127.0.0.1 8885 "hola!" 127.0.0.1 8881 10 347

# paquete de 150 bytes totales: 18 de header + 132 de mensaje
MENSAJE150=$(python3 -c "print('x' * 132)")
python3 enviar.py 127.0.0.1 8885 "$MENSAJE150" 127.0.0.1 8881 10 347
sleep 2

echo "=== R1 ==="; cat "$LOGDIR/R1.log"
echo "=== R2 ==="; cat "$LOGDIR/R2.log"
echo "=== R3 ==="; cat "$LOGDIR/R3.log"
echo "=== R4 ==="; cat "$LOGDIR/R4.log"
echo "=== R5 ==="; cat "$LOGDIR/R5.log"

pkill -f "router.py" 2>/dev/null
