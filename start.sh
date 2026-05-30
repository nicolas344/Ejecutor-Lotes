#!/bin/bash
# Rutas de tuberias y aralmac
ARALMAC=/tmp/aralmac

TB_GESFICH_REQ=/tmp/tb_gesfich_req
TB_GESFICH_RES=/tmp/tb_gesfich_res
TB_GESPROG_REQ=/tmp/tb_gesprog_req
TB_GESPROG_RES=/tmp/tb_gesprog_res
TB_EJECUTOR_REQ=/tmp/tb_ejecutor_req
TB_EJECUTOR_RES=/tmp/tb_ejecutor_res
TB_CLIENTE_REQ=/tmp/tb_cliente_req
TB_CLIENTE_RES=/tmp/tb_cliente_res

# Limpiar tuberias anteriores
rm -f $TB_GESFICH_REQ $TB_GESFICH_RES \
       $TB_GESPROG_REQ $TB_GESPROG_RES \
       $TB_EJECUTOR_REQ $TB_EJECUTOR_RES \
       $TB_CLIENTE_REQ $TB_CLIENTE_RES

echo "Arrancando ctrllt (crea tuberias)..."

python3 src/ctrllt/ctrllt.py \
  -c $TB_CLIENTE_REQ -a $TB_CLIENTE_RES \
  -f $TB_GESFICH_REQ -b $TB_GESFICH_RES \
  -p $TB_GESPROG_REQ -r $TB_GESPROG_RES \
  -e $TB_EJECUTOR_REQ -d $TB_EJECUTOR_RES &

sleep 0.3

echo "Arrancando servicios..."

python3 src/gesfich/gesfich.py -f $TB_GESFICH_REQ -b $TB_GESFICH_RES -x $ARALMAC &
python3 src/gesprog/gesprog.py -p $TB_GESPROG_REQ -c $TB_GESPROG_RES -x $ARALMAC &
python3 src/ejecutor/ejecutor.py -e $TB_EJECUTOR_REQ -d $TB_EJECUTOR_RES -x $ARALMAC &

sleep 0.5

echo "Arrancando cliente..."
python3 src/cliente/cliente.py -c $TB_CLIENTE_REQ -a $TB_CLIENTE_RES
