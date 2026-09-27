# El Bachaco Financiero v1

Aplicación local de finanzas personales con Python + SQLite.

## Ejecutar en Windows

1. Asegúrate de tener Python instalado.
2. Ejecuta `run.bat` o abre CMD en esta carpeta y ejecuta:

```bat
python server.py
```

3. Abre `http://localhost:3000`.

## Cambios de v1.2

- Se corrige el cálculo de Dinero Corriente, Dinero Ahorro y Neto Real: el porcentaje de ahorro se aplica sobre el dinero que queda después de gastos. El Neto Real siempre es Corriente + Ahorro.
- Se ajusta el diseño de la interfaz para que sea más clara y fácil de usar. Dispositivos moviles
- Se puede cambiar el tipo de ahorro, (Automatico o Manual) y el porcentaje de ahorro, en la sección de Ahorros.

## Pendiente

- Subirlo a internet para que sea accesible desde cualquier lugar.
- Medidas de seguridad para proteger los datos de los usuarios.
- Añadir espacio de Registro, dentro del usuario opcion de eliminar cuenta y datos
