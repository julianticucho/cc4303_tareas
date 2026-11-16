#!/bin/bash
# test_reensamblado.sh :: red de 5 routers con MTU y re-ensamblado activo.
# Envia un paquete chico y tres paquetes de 150 bytes con IDs distintos desde
# R1 a R5: R5 debe imprimir "hola!" y tres lineas completas de 132 x.
# Logs del escenario en logs/reensamblado/

pkill -f "router.py" 2>/dev/null
sleep 0.5

LOGDIR=logs/reensamblado
mkdir -p "$LOGDIR"

python3 -u router.py 127.0.0.1 8881 rutas/rutas_R1_v3_mtu.txt > "$LOGDIR/R1.log" 2>&1 &
python3 -u router.py 127.0.0.1 8882 rutas/rutas_R2_v3_mtu.txt > "$LOGDIR/R2.log" 2>&1 &
python3 -u router.py 127.0.0.1 8883 rutas/rutas_R3_v3_mtu.txt > "$LOGDIR/R3.log" 2>&1 &
python3 -u router.py 127.0.0.1 8884 rutas/rutas_R4_v3_mtu.txt > "$LOGDIR/R4.log" 2>&1 &
python3 -u router.py 127.0.0.1 8885 rutas/rutas_R5_v3_mtu.txt > "$LOGDIR/R5.log" 2>&1 &
sleep 1

python3 enviar.py 127.0.0.1 8885 "hola!" 127.0.0.1 8881 10 347

MENSAJE150=$(python3 -c "print('x' * 132)")
python3 enviar.py 127.0.0.1 8885 "$MENSAJE150" 127.0.0.1 8881 10 347
python3 enviar.py 127.0.0.1 8885 "$MENSAJE150" 127.0.0.1 8881 10 348
python3 enviar.py 127.0.0.1 8885 "$MENSAJE150" 127.0.0.1 8881 10 349
sleep 2

echo "=== R5 (solo llega lo re-ensamblado) ==="; cat "$LOGDIR/R5.log"

pkill -f "router.py" 2>/dev/null
