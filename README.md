## El Bachaco Financiero v4.1 corregida

Esta versión corrige el cálculo de Dinero Corriente, Dinero Ahorro y Neto Real: el porcentaje de ahorro se aplica sobre el dinero que queda después de gastos. El Neto Real siempre es Corriente + Ahorro.

# El Bachaco Financiero v4.1

Aplicación local de finanzas personales con Python + SQLite.

## Ejecutar en Windows

1. Asegúrate de tener Python instalado.
2. Ejecuta `run.bat` o abre CMD en esta carpeta y ejecuta:

```bat
python server.py
```

3. Abre `http://localhost:3000`.

## Cambios de v4.1

- Resumen inicial reorganizado en: Ingresos, Gastos, Dinero corriente (Ocio), Dinero ahorro, Neto real y Tasa de ahorro calculada.
- El ahorro objetivo se aparta primero según la tasa configurada.
- El gasto reduce primero el dinero corriente.
- Cuando el dinero corriente pasa a negativo, el exceso empieza a consumir el ahorro apartado.
- La tasa de ahorro se recalcula sobre el ahorro que realmente queda.
- Dinero corriente, ahorro y neto real negativos se muestran en rojo.
- `index.html` se sirve con `no-cache` para evitar que Chrome muestre versiones antiguas durante el desarrollo.
- `run.bat` está dentro de la carpeta correcta, junto a `server.py`.
