# Recurrente: Documentación API

La API de Recurrente te permite crear sesiones de compra, manejar tus productos, suscripciones, y clientes, hacer transferencias de dinero entre diferentes cuentas de Recurrente, y mucho más.

## **Cómo empezar**

* [Crea una cuenta](http://app.recurrente.com/bienvenida) en Recurrente.
* La API responde en formato JSON. Cuando retorna un error, el error es enviado en un *error key* en JSON.

## Autenticación

Para encontrar tus Llaves de API, dentro de tu cuenta de Recurrente, ve a:

**Configuración** → **Llaves API.**

Para autenticarte, debes enviar los siguientes headers en cada request:

| Header                        | Description      |
| ----------------------------- | ---------------- |
| `<span>X-PUBLIC-KEY</span>` | tu_llave_publica |
| `<span>X-SECRET-KEY</span>` | tu_llave_privada |

### Error en la autenticación

Si tus llaves de API no se están enviando o son inválidas, recibirás un código de respuesta HTTP 401 Unauthorized.

### Sandbox y pagos de prueba

Existen dos formas de realizar pruebas: usando el **ambiente Sandbox** o haciendo pruebas directamente en  **producción** , dependiendo del tipo de validación que necesites.

#### ✅ Ambiente Sandbox

El ambiente Sandbox permite hacer pagos de prueba sin generar actividad real. Para utilizarlo:

* Usa tus llaves de ambiente  **TEST** .
* Simula un pago exitoso con la tarjeta  **4242 4242 4242 4242** .

Los checkouts creados con llaves TEST:

* Muestran un aviso que dice **"PRUEBA"** en el link de pago.
* Tienen el atributo `<span>live_mode = false</span>`.
* **No** crean actividad en la cuenta ni afectan el balance.
* **No** disparan webhooks.

> Este ambiente es ideal para pruebas durante la integración inicial o desarrollo.

#### ⚠️ Pruebas en producción

También es posible realizar pruebas en ambiente **LIVE** con tus llaves de producción. En estos casos:

* Se recomienda  **reembolsar los pagos de prueba el mismo día** , ya sea desde el panel de Recurrente o mediante la API en `<span>/api/refunds</span>`.
* Los pagos reembolsados el mismo día son reembolsados al  **100% del monto** .

> Esta opción permite validar el flujo completo, incluyendo actividad en cuenta, webhooks y conciliación.

### **¿Necesitas ayuda?**

* Si estás usando Wordpress, te recomendamos que utilices [nuestro plugin](https://ayuda.recurrente.com/es/articles/8971522-como-instalo-el-plugin-de-recurrente-en-woocommerce).
* Únete y pregunta en nuestro [Discord](https://discord.gg/QhKPEkSKp2).
* O envíanos un correo a [soporte@recurrente.com](https://mailto:soporte@recurrente.com/)



## Prueba tu autenticación

Envía un request de prueba para confirmar que tu autenticación está funcionando correctamente.

### GET**Test**

**https://app.recurrente.com/api/test**

Incluye los headers de autenticación y un "body" vacío, y recibe una respuesta con el nombre de tu cuenta.

json

```json
{}
```

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

**Content-Type**

application/json

PARAMS

**hola**

adios

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json

conn = http.client.HTTPSConnection("app.recurrente.com")
payload = ''
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-Type': 'application/json'
}
conn.request("GET", "/api/test", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**200 OK**

Example Response

* **Body**
* **Headers (0)**

json

```json
{
  "message": "Hello La Surf Office 🌎"
}
```



## Checkouts

###### ¿Qué es un Checkout?

Un `<span>Checkout</span>` te entrega un link a una página de compra a la cuál debes redirigir a tu usuario.

Puedes usar checkouts para:

* Un pago único
* Iniciar una suscripción

###### ¿Cómo determinar el monto a pagar en un Checkout?

Existen dos formas de determinar el monto en un checkout:

* Creando los "items" que quiero añadir al checkout directo desde el request.
* Pasando el "Price ID" de los productos que quiero añadir.

En esta sección encontrarás ejemplos de ambos casos.

###### ¿Cómo saber si el usuario ya completó el pago?

Para saber si el usuario ya completó el pago, tú puedes revisar el estado de la compra de dos maneras:

* Utilizando [webhooks](https://documenter.getpostman.com/view/10340859/2sA2rFQf5R#785a531d-b59d-4943-b9e8-26119a1aed7c)  **(recomendada)** .
* Llamando a "GET Checkout" con el ID del checkout, y revisando el estado ahí.

###### ¿Cómo hacer un pago de prueba?

Para hacer pagos de prueba, utiliza tus llaves de ambiente **TEST.** Para realizar un pago exitoso, debes utilizar la tarjeta 4242 4242 4242 4242.

Checkouts creados con llaves test serán diferentes a los checkouts LIVE de las siguientes maneras:

* Tendrán un aviso que dirá "PRUEBA" en el link de pago.
* Tendrán el atributo `<span>live_mode = false</span>`.
* No crearán actividad en la cuenta, ni incrementarán el balance.
* No se enviarán webhooks.

###### Customizar métodos de pago

Para customizar métodos de pago:

* Debe ir incluido `<span>custom_payment_method_settings: true</span>`, de lo contrario, el producto regresa a utilizar los defaults de la cuenta.
* Para no ofrecer cuotas, `<span>available_installments</span>` debe ser un array vacío `<span>[]</span>`

Ejemplo:

View More

json

```json
{ 
  "product": { 
    "name": "El nombre del producto",
    "custom_payment_method_settings": "true",
    "card_payments_enabled": "true",
    "bank_transfer_payments_enabled": "true",
    "available_installments": [3, 6, 12, 18],
    "prices_attributes": [
      { 
        "amount_in_cents": "10000",
        "charge_type": "one_time",
        "currency": "GTQ"
      }
    ]
  }
}
```

###### Expirar un checkout

Puedes expirar un checkout utilizando el atributo de `<span>expires_at</span>`.

Puedes ponerle una fecha futura (fecha y hora en la que va a expirar), o una fecha pasada (para que se expire instantáneamente).

###### Customizar apariencia

Customiza la apariencia de tus checkouts desde **Ajustes -> Tienda -> Apariencia.**

Podrás añadir *color de fondo,* *color de acento,* y escoger la Fuente (tipografía) que quieras.



### POST**Create a checkout (item details)**

**https://app.recurrente.com/api/checkouts/**

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Bodyformdata

**items[][name]**

One Ripe Banana

El nombre del producto.

**items[][currency]**

GTQ

La moneda a cobrar.

Posibles valores son:

* GTQ
* USD

**items[][amount_in_cents]**

3000

Monto a cobrar en centavos.

**items[][image_url]**

https://www.sourcesplash.com/explore/food

(Opcional) URL de la imagen del producto.

**items[][quantity]**

1

(Opcional) Cantidad.

Si no incluyes una, el default es 1.

El valor mínimo es 1 y el valor máximo es 9.

**items[][has_dynamic_pricing]**

false

(Opcional) Indica si el producto debe usar precio dinámico. El precio se convierte en el "monto a recibir" neto por el comercio. Disponible solo para pagos únicos.

**success_url**

https://www.google.com

(Opcional) URL a dónde dirigir al comprador después de un pago exitoso.

**cancel_url**

https://www.amazon.com

(Opcional) URL a dónde dirigir al comprador cuando abandona el checkout.

**user_id**

us_123456

(Opcional) ID del usuario a quien pertenece el checkout. Prepopula los campos de información de usuario (Nombre, Email, etc.)

**metadata**

{}

(Opcional) Puedes utilizar metadata para almacenar información estructurada adicional sobre un producto.

Puedes especificar hasta 50 keys, con nombres de hasta 40 caracteres y valores de hasta 500 caracteres.

**expires_at**

(Opcional) Fecha en la que quieres que el checkout expire, en formato ISO 8601. Por ejemplo: "2050-05-15T13:45:30Z"

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json

conn = http.client.HTTPSConnection("app.recurrente.com")
payload = json.dumps({
  "items": [
    {
      "name": "One Ripe Banana",
      "currency": "GTQ",
      "amount_in_cents": 3000,
      "image_url": "https://source.unsplash.com/400x400/?banana",
      "quantity": 1
    }
  ],
  "success_url": "https://www.google.com",
  "cancel_url": "https://www.amazon.com",
  "user_id": "us_123456",
  "metadata": {}
})
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-Type': 'application/json'
}
conn.request("POST", "/api/checkouts", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**201 Created**

Example Response

* **Body**
* **Headers (0)**

json

```json
{
  "id": "ch_eegw9j5zgqoae3ms",
  "checkout_url": "https://app.recurrente.com/checkout-session/ch_eegw9j5zgqoae3ms"
}
```


### POST**Create a checkout (item details: subscription)**

**https://app.recurrente.com/api/checkouts/**

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Bodyformdata

**items[][name]**

Membersía Gold

El nombre de la suscripción.

**items[][currency]**

GTQ

La moneda a cobrar.

Posibles valores son:

* GTQ
* USD

**items[][amount_in_cents]**

3000

Monto a cobrar en centavos.

**items[][image_url]**

https://source.unsplash.com/400x400/?banana

(Opcional) URL de la imagen del producto.

**items[][quantity]**

1

(Opcional) Cantidad.

Si no incluyes una, el default es 1.

El valor mínimo es 1 y el valor máximo es 9.

**success_url**

https://www.google.com

(Opcional) URL a dónde dirigir al comprador después de un pago exitoso.

**cancel_url**

https://www.amazon.com

(Opcional) URL a dónde dirigir al comprador cuando abandona el checkout.

**user_id**

us_123456

(Opcional) ID del usuario a quien pertenece el checkout. Prepopula los campos de información de usuario (Nombre, Email, etc.)

**metadata**

{}

(Opcional) Puedes utilizar metadata para almacenar información estructurada adicional sobre un producto.

Puedes especificar hasta 50 keys, con nombres de hasta 40 caracteres y valores de hasta 500 caracteres.

**items[][charge_type]**

recurring

Tipo de cargo: recurrente

**items[][billing_interval]**

month

Intervalo de tiempo de pago Opciones:

* week
* month
* year

**items[][billing_interval_count]**

1

Cantidad de intervalos de pago

**items[][periods_before_automatic_cancellation]**

12

(Opcional) Periodos a cobrar antes de que se cancele automáticamente

**items[][free_trial_interval]**

month

(Opcional) Intervalo de período de prueba Opciones:

* week
* month
* year

**items[][free_trial_interval_count]**

1

(Opcional) Cantidad de intervalos de período de prueba

**items[][has_dynamic_pricing]**

true

(Opcional) El precio cambia dependiendo del método de pago que elige el cliente — Tú recibes el monto a cobrar completo. Todos los métodos de pago se activan. Funciona solo para pagos únicos.

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json

conn = http.client.HTTPSConnection("app.recurrente.com")
payload = json.dumps({
  "items": [
    {
      "name": "Membresia Gold",
      "description": "Suscripción con un mes de prueba",
      "currency": "GTQ",
      "amount_in_cents": 5000,
      "charge_type": "recurring",
      "image_url": "https://source.unsplash.com/400x400/?banana",
      "custom_terms_and_conditions": "Terminos y condiciones",
      "billing_interval_count": 1,
      "billing_interval": "month",
      "periods_before_automatic_cancellation": 12,
      "free_trial_interval_count": 1,
      "free_trial_interval": "month",
      "metadata": {}
    }
  ],
  "success_url": "https://www.google.com",
  "cancel_url": "https://www.amazon.com",
  "metadata": {}
})
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-Type': 'application/json'
}
conn.request("POST", "/api/checkouts", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**201 Created**

Example Response

* **Body**
* **Headers (0)**

json

```json
{
  "id": "ch_eegw9j5zgqoae3ms",
  "checkout_url": "https://app.recurrente.com/checkout-session/ch_eegw9j5zgqoae3ms"
}
```




### POST**Create a checkout (Product ID)**

**https://app.recurrente.com/api/checkouts/**

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Bodyformdata

**items[][product_id]**

prod_1234567

Crea un producto primero, y luego utiliza el ID del producto.

**success_url**

https://www.google.com

(Opcional) URL a dónde dirigir al comprador después de un pago exitoso.

**cancel_url**

https://www.amazon.com

(Opcional) URL a dónde dirigir al comprador cuando abandona el checkout.

**user_id**

us_123456

(Opcional) ID del usuario a quien pertenece el checkout. Prepopula los campos de información de usuario (Nombre, Email, etc.)

**metadata**

{}

(Opcional) Puedes utilizar metadata para almacenar información estructurada adicional sobre un producto.

Puedes especificar hasta 50 keys, con nombres de hasta 40 caracteres y valores de hasta 500 caracteres.

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json

conn = http.client.HTTPSConnection("app.recurrente.com")
payload = json.dumps({
  "items": [
    {
      "product_id": "prod_123456"
    }
  ],
  "metadata": {}
})
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-Type': 'application/json'
}
conn.request("POST", "/api/checkouts", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**201 Created**

Example Response

* **Body**
* **Headers (0)**

json

```json
{
  "id": "ch_eegw9j5zgqoae3ms",
  "checkout_url": "https://app.recurrente.com/checkout-session/ch_eegw9j5zgqoae3ms"
}
```



### PATCH**Update a checkout**

**https://app.recurrente.com/api/checkouts/{{checkoutId}}**

## Descripción del Endpoint

Este endpoint permite actualizar un checkout existente en la plataforma de Recurrente. Solo se permiten ediciones a checkouts que  **no han sido pagados** , en los campos a continuación.

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Bodyformdata

**success_url**

https://www.google.com

(Opcional) URL a dónde dirigir al comprador después de un pago exitoso.

**cancel_url**

https://www.amazon.com

(Opcional) URL a dónde dirigir al comprador cuando abandona el checkout.

**metadata**

{ "internalID: 123 }

(Opcional) Puedes utilizar metadata para almacenar información estructurada adicional sobre un producto.

Puedes especificar hasta 50 keys, con nombres de hasta 40 caracteres y valores de hasta 500 caracteres.

**expires_at**

"2050-05-15T13:45:30Z"

(Opcional) Fecha en la que quieres que el checkout expire, en formato ISO 8601. Por ejemplo: "2050-05-15T13:45:30Z"

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json

conn = http.client.HTTPSConnection("app.recurrente.com")
payload = json.dumps({
  "items": [
    {
      "name": "One Ripe Banana",
      "currency": "GTQ",
      "amount_in_cents": 3000,
      "image_url": "https://source.unsplash.com/400x400/?banana",
      "quantity": 1
    }
  ],
  "success_url": "https://www.google.com",
  "cancel_url": "https://www.amazon.com",
  "user_id": "us_123456",
  "metadata": {}
})
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-Type': 'application/json'
}
conn.request("POST", "/api/checkouts", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**201 Created**

Example Response

* **Body**
* **Headers (0)**

View More

json

```json
{
    "id": "ch_eegw9j5zgqoae3ms",
    "status": "unpaid",
    "payment": null,
    "payment_method": null,
    "transfer_setups": [],
    "metadata": {
        "internalID": 123
    },
    "expires_at": "2050-05-15T13:45:30Z",
    "success_url": "https://google.com",
    "cancel_url": "https://amazon.com",
    "created_at": "2025-05-15T13:45:30Z",
    "total_in_cents": "500",
    "currency": "GTQ",
    "latest_intent": { 
        "id": "pa_123", 
        "created_at": "2025-05-15T13:45:30Z",
        "type": "PaymentIntent", 
        data: { 
            "auth_code": "123456" 
        } 
    }
}
```


### GET**Get a checkout**

**https://app.recurrente.com/api/checkouts/{{checkoutId}}**

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Example Request

No pagado

[ ]

View More

python

```python
import http.client
import json
import mimetypes
from codecs import encode

conn = http.client.HTTPSConnection("app.recurrente.com")
dataList = []
boundary = 'wL36Yn8afVp8Ag7AmP8qZ0SA4n1v9T'
dataList.append(encode('--' + boundary))
dataList.append(encode('Content-Disposition: form-data; name=mode;'))

dataList.append(encode('Content-Type: {}'.format('text/plain')))
dataList.append(encode(''))

dataList.append(encode("setup"))
dataList.append(encode('--'+boundary+'--'))
dataList.append(encode(''))
body = b'\r\n'.join(dataList)
payload = body
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-type': 'multipart/form-data; boundary={}'.format(boundary)
}
conn.request("GET", "/api/checkouts/{{checkoutId}}", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**200 OK**

Example Response

* **Body**
* **Headers (0)**

View More

json

```json
{
  "id": "ch_eegw9j5zgqoae3ms",
  "status": "unpaid",
  "payment": null,
  "payment_method": null,
  "transfer_setups": [],
  "metadata": {},
  "expires_at": "2050-05-15T13:45:30Z",
  "success_url": "https://google.com",
  "cancel_url": "https://amazon.com",
  "created_at": "2025-05-15T13:45:30Z",
  "total_in_cents": "500",
```



### GET**Get all checkouts**

**https://app.recurrente.com/api/checkouts?from_time=2050-05-15T13:45:30Z&until_time=2050-05-15T13:45:30Z&user_id=us_123&page=1&items=20**

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

PARAMS

**from_time**

2050-05-15T13:45:30Z

(Opcional) Fecha y hora a partir de la cual quieres filtrar los checkouts, en formato ISO 8601. Por ejemplo: "2024-05-15T13:45:30Z".

**until_time**

2050-05-15T13:45:30Z

(Opcional) Fecha y hora hasta la cual quieres filtrar los checkouts, en formato ISO 8601. Por ejemplo: "2024-05-15T13:45:30Z"

**user_id**

us_123

(Opcional) ID del usuario para filtrar los checkouts asociados a él. Por ejemplo: "us_123".

**page**

1

(Opcional) Número de página actual que deseas visualizar.

**items**

20

(Opcional) Cantidad de elementos que se deben mostrar por página.

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json
import mimetypes
from codecs import encode

conn = http.client.HTTPSConnection("app.recurrente.com")
boundary = ''
payload = ''
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-type': 'multipart/form-data; boundary={}'.format(boundary)
}
conn.request("GET", "/api/checkouts?from_time=2024-05-15T13:45:30Z&until_time=2050-05-15T13:45:30Z&user_id=us_123", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**200 OK**

Example Response

* **Body**
* **Headers (0)**

View More

json

```json
[{
    "id": "ch_lmgbvesmihkqzma3",
    "status": "paid",
    "payment": {
        "id": "pa_ttfeprgn",
        "paymentable": {
            "type": "Subscription",
            "id": "su_nehndm7j",
            "tax_name": null,
            "tax_id": null
        }
    },
    "payment_method": {
        "id": "pay_m_ru4ztzg3",
        "type": "card",
        "card": {
            "last4": "4242",
            "network": "visa"
        }
    },
    "transfer_setups": [],
    "metadata": {},
    "expires_at": "2050-05-15T13:45:30Z",
    "success_url": "https://google.com",
    "cancel_url": "https://amazon.com",
    "created_at": "2025-05-15T13:45:30Z",
    "total_in_cents": "500",
    "currency": "GTQ",
    "latest_intent": { 
        "id": "pa_123", 
        "created_at": "2025-05-15T13:45:30Z",
        "type": "PaymentIntent", 
        data: { 
            "auth_code": "123456" 
        } 
    }
}]
```


PATCH**Update a payment intent**

**https://app.recurrente.com/api/payment_intents/{{paymentIntentId}}**

Para actualizar la factura de un pago, debés pasar el parámetro de `<span>tax_invoice_url</span>`, como se muestra en el ejemplo.

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Bodyformdata

**payment_intent[tax_invoice_url]**

"https://example.com/factura123"

El URL de la factura electrónica

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json

conn = http.client.HTTPSConnection("app.recurrente.com")
payload = json.dumps({
  "payment_intent": {
    "tax_invoice_url": "https://www.example.com/factura123"
  }
})
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-Type': 'application/json'
}
conn.request("PATCH", "/api/invoices/{{invoiceId}}", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**200 OK**

Example Response

* **Body**
* **Headers (0)**

View More

json

```json
{
  "id": "pa_123",
  "checkout": {
    "id": "ch_123"
  },
  "api_version": "2024-04-24",
  "created_at": "2023-09-27T09:07:25.119-06:00",
  "failure_reason": null,
  "customer_id": "us_123",
  "amount_in_cents": 500,
  "currency": "GTQ",
  "fee": 223,
  "vat_withheld": 0,
  "vat_withheld_currency": "GTQ",
  "product": {
    "id": "prod_123"
  },
  "products": [
    {
      "id": "prod_123",
      "status": "active",
      "name": "Banana",
      "description": null,
      "success_url": null,
      "cancel_url": null,
      "custom_terms_and_conditions": null,
      "phone_requirement": "none",
      "address_requirement": "none",
      "billing_info_requirement": "optional",
      "prices": [
        {
          "id": "price_123",
          "amount_in_cents": 500,
          "currency": "GTQ",
          "billing_interval_count": 0,
          "billing_interval": "",
          "charge_type": "one_time",
          "periods_before_automatic_cancellation": null,
          "free_trial_interval_count": 0,
          "free_trial_interval": ""
        }
      ],
      "storefront_link": "app.recurrente.com/s/surf-office/banana",
      "metadata": {}
    }
  ],
  "customer": {
    "id": "us_123",
    "email": "dev@example.com",
    "full_name": "Mario Bros"
  },
  "payment": {
    "id": "pa_123",
    "paymentable": {
      "type": "OneTimePayment",
      "id": "on_ekhaj3ps",
      "tax_name": "",
      "tax_id": "",
      "address": null,
      "phone_number": null
    }
  },
  "tax_invoice_url": "https://www.example.com/factura123"
}
```



## Products

Puedes crear dos tipos de productos:

* Cobro único `<span>one_time</span>`
* Suscripción `<span>recurring</span>`

Abajo encontrarás los requests para ambos.

### POST**Create a product (one time payment)**

**https://app.recurrente.com/api/products/**

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

**Content-Type**

application/json

Bodyformdata

**product[name]**

El nombre de tu producto

El nombre del producto.

**product[description]**

La descripción es opcional

(Opcional)

**product[image_url]**

https://source.unsplash.com/400x400/?banana

(Opcional) URL de la imagen del producto.

**product[prices_attributes[][currency]]**

GTQ

Posibles valores son:

* GTQ
* USD

**product[prices_attributes[][charge_type]]**

one_time

**product[prices_attributes[][amount_in_cents]]**

1000

(Opcional) Cantidad.

**product[cancel_url]**

https://www.amazon.com/

(Opcional) URL a dónde dirigir al comprador después de un pago exitoso.

**product[success_url]**

https://www.google.com/

(Opcional) URL a dónde dirigir al comprador cuando abandona el checkout.

**product[custom_terms_and_conditions]**

El texto que tú quieras añadir.

(Opcional)

**product[phone_requirement]**

none

Los valores posibles son:

* required
* optional
* none

**product[address_requirement]**

none

(Opcional) Si deseas capturar dirección de entrega en el checkout. Los valores posibles son:

* required
* optional
* none

**product[billing_info_requirement]**

none

(Opcional) Si deseas capturar NIT/Pasaporte en el checkout. Los valores posibles son:

* required
* optional
* none

**product[adjustable_quantity]**

true

(Opcional) Esto determina si el comprador puede ajustar la cantidad de unidades a comprar de este producto.

Si lo dejas en blanco, el valor es "true". Puedes cambiarlo a "false".

**product[metadata]**

{}

(Opcional) Puedes utilizar metadata para almacenar información estructurada adicional sobre un producto.

Puedes especificar hasta 50 keys, con nombres de hasta 40 caracteres y valores de hasta 500 caracteres.

**product[inventory_quantity]**

(Opcional) Puedes dejarlo vacío si no quieres llevar una cantidad de inventario. Cada compra va reduciendo el inventario disponible, hasta que el producto llega a 0 disponible y se deshabilita.

**product[has_dynamic_pricing]**

(Opcional) Añade precio dinámico. El precio se convierte en el "monto a recibir" neto por el comercio. Disponible solo para pagos únicos.

Example Request

Ejemplo

[ ]

View More

python

```python
import http.client
import json

conn = http.client.HTTPSConnection("app.recurrente.com")
payload = json.dumps({
  "product": {
    "name": "El nombre de tu producto",
    "description": "La descripción es opcional",
    "image_url": "https://source.unsplash.com/400x400/?banana",
    "prices_attributes": [
      {
        "currency": "GTQ",
        "charge_type": "one_time",
        "amount_in_cents": 500
      }
    ],
    "cancel_url": "https://www.amazon.com/",
    "success_url": "https://www.google.com/",
    "custom_terms_and_conditions": "El texto que tú quieras añadir.",
    "phone_requirement": "none",
    "address_requirement": "none",
    "billing_info_requirement": "none"
  },
  "adjustable_quantity": True,
  "inventory_quantity": None,
  "metadata": {}
})
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-Type': 'application/json'
}
conn.request("POST", "/api/products/", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**201 Created**

Example Response

* **Body**
* **Headers (0)**

View More

json

```json
{
  "id": "prod_9lstwgbr",
  "status": "active",
  "name": "El nombre de tu producto",
  "description": "Descripción del producto",
  "success_url": "https://www.google.com/",
  "cancel_url": "https://www.amazon.com/",
  "custom_terms_and_conditions": "Términos y condiciones",
  "phone_requirement": "none",
  "address_requirement": "none",
  "billing_info_requirement": "none",
  "prices": [
```



### POST**Create a product (subscription)**

**https://app.recurrente.com/api/products/**

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Bodyformdata

**product[name]**

El nombre de tu producto

El nombre del producto.

**product[description]**

La descripción es opcional

(Opcional)

**product[image_url]**

https://source.unsplash.com/400x400/?banana

La moneda a cobrar.

Posibles valores son:

* GTQ
* USD

**product[prices_attributes[][currency]]**

GTQ

Monto a cobrar en centavos.

**product[prices_attributes[][charge_type]]**

recurring

(Opcional) URL de la imagen del producto.

**product[prices_attributes[][amount_in_cents]]**

1000

(Opcional) Cantidad.

Si no incluyes una, el default es 1.

**product[cancel_url]**

https://www.amazon.com/

(Opcional) URL a dónde dirigir al comprador después de un pago exitoso.

**product[success_url]**

https://www.google.com/

(Opcional) URL a dónde dirigir al comprador cuando abandona el checkout.

**product[custom_terms_and_conditions]**

El texto que tú quieras añadir.

(Opcional)

**product[phone_requirement]**

none

Los valores posibles son:

* required
* optional
* none

**product[address_requirement]**

none

Los valores posibles son:

* required
* optional
* none

**product[billing_info_requirement]**

none

Los valores posibles son:

* optional
* none

**adjustable_quantity**

true

(Opcional) Esto determina si el comprador puede ajustar la cantidad de unidades a comprar de este producto.

Si lo dejas en blanco, el valor es "true". Puedes cambiarlo a "false".

**product[prices_attributes[][billing_interval_count]]**

1

Cada cuánto quieres cobrar la suscripción en número (e.g. 1 mes, 2 meses)

**product[prices_attributes[][billing_interval]]**

month

Qué plazo quieres usar para cobrar la suscripción. Los valores posibles son:

* month
* week
* year

**product[prices_attributes[][free_trial_interval_count]]**

1

(Opcional) Cuánto quieres dar de periodo de prueba gratuito.

**product[prices_attributes[][free_trial_interval]]**

month

(Opcional) Qué plazo quieres usar para el período de prueba. Los valores posibles son:

* month
* week
* year

**product[prices_attributes[][periods_before_automatic_cancellation]]**

(Opcional) Cuántos periodos quieres que pasen antes de que la suscripción se cancele automáticamente. Si lo dejas en blanco, la suscripción se continuará conbrando indefinidamente.

**product[prices_attributes[][periods_before_allowed_to_cancel]]**

(Opcional) Cuántos periodos quieres que pasen antes de permitir que el cliente pueda cancelar su suscripción. Ojo, las suscripciones igual pueden cancelarse por falta de fondos en la tarjeta, tarjeta expirada, y otras razones.

**metadata**

{}

(Opcional) Puedes utilizar metadata para almacenar información estructurada adicional sobre un producto.

Puedes especificar hasta 50 keys, con nombres de hasta 40 caracteres y valores de hasta 500 caracteres.

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json

conn = http.client.HTTPSConnection("app.recurrente.com")
payload = json.dumps({
  "product": {
    "name": "El nombre de tu producto",
    "description": "Descripción del producto",
    "success_url": "https://www.google.com/",
    "cancel_url": "https://www.amazon.com/",
    "custom_terms_and_conditions": "Términos y condiciones",
    "phone_requirement": "none",
    "address_requirement": "none",
    "billing_info_requirement": "none",
    "prices_attributes": [
      {
        "amount_in_cents": 1000,
        "currency": "GTQ",
        "billing_interval_count": 1,
        "billing_interval": "month",
        "charge_type": "recurring",
        "periods_before_automatic_cancellation": "",
        "free_trial_interval_count": 1,
        "free_trial_interval": "month"
      }
    ],
    "metadata": {}
  }
})
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-Type': 'application/json'
}
conn.request("POST", "/api/products/", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**201 Created**

Example Response

* **Body**
* **Headers (0)**

View More

json

```json
{
  "id": "prod_vsyjzsqf",
  "status": "active",
  "name": "El nombre de tu producto",
  "description": "Descripción del producto",
  "success_url": "https://www.google.com/",
  "cancel_url": "https://www.amazon.com/",
  "custom_terms_and_conditions": "Términos y condiciones",
  "phone_requirement": "none",
  "address_requirement": "none",
  "billing_info_requirement": "none",
  "prices": [
    {
      "id": "price_tnxd8fzw",
      "amount_in_cents": 1000,
      "currency": "GTQ",
      "billing_interval_count": 1,
      "billing_interval": "month",
      "charge_type": "recurring",
      "periods_before_automatic_cancellation": null,
      "free_trial_interval_count": 1,
      "free_trial_interval": "month"
    }
  ],
  "storefront_link": "https://app.recurrente.com/s/surf-office/el-nombre-de-tu-producto-f9ljtq",
  "metadata": {}
}
```


### GET**Get a product**

**https://app.recurrente.com/api/products/{{productId}}**

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json
import mimetypes
from codecs import encode

conn = http.client.HTTPSConnection("app.recurrente.com")
boundary = ''
payload = ''
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-type': 'multipart/form-data; boundary={}'.format(boundary)
}
conn.request("GET", "/api/products/{{productId}}", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**200 OK**

Example Response

* **Body**
* **Headers (24)**

View More

json

```json
{
  "id": "prod_9lstwgbr",
  "status": "active",
  "name": "El nombre de tu producto",
  "description": "Descripción de tu producto",
  "success_url": "https://www.google.com/",
  "cancel_url": "https://www.amazon.com/",
  "custom_terms_and_conditions": "Términos y condiciones",
  "phone_requirement": "none",
  "address_requirement": "none",
  "billing_info_requirement": "none",
  "prices": [
```



### GET**Get all products**

**https://app.recurrente.com/api/products**

Por defecto, se muestran los 10 productos más recientes. Para obtener los siguientes 10 productos, agrega query params.

Ejemplo: [https://app.recurrente.com/api/products?page=2](https://app.recurrente.com/api/subscriptions?page=2)

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json
import mimetypes
from codecs import encode

conn = http.client.HTTPSConnection("app.recurrente.com")
boundary = ''
payload = ''
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-type': 'multipart/form-data; boundary={}'.format(boundary)
}
conn.request("GET", "/api/products", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**200 OK**

Example Response

* **Body**
* **Headers (0)**

View More

json

```json
[
  {
    "id": "prod_9lstwgbr",
    "status": "active",
    "name": "El nombre de tu producto",
    "description": "Descripción de tu producto",
    "success_url": "https://www.google.com/",
    "cancel_url": "https://www.amazon.com/",
    "custom_terms_and_conditions": "Términos y condiciones",
    "phone_requirement": "none",
    "address_requirement": "none",
    "billing_info_requirement": "none",
    "prices": [
      {
        "id": "price_rky4dog7",
        "amount_in_cents": 500,
        "currency": "GTQ",
        "billing_interval_count": 0,
        "billing_interval": "",
        "charge_type": "one_time",
        "periods_before_automatic_cancellation": null,
        "free_trial_interval_count": 0,
        "free_trial_interval": ""
      }
    ],
    "storefront_link": "https://app.recurrente.com/s/surf-office/el-nombre-de-tu-producto",
    "metadata": {}
  },
  {
    "id": "prod_psstwgbr",
    "status": "active",
    "name": "El nombre de tu producto 2",
    "description": "Descripción de tu producto",
    "success_url": "https://www.google.com/",
    "cancel_url": "https://www.amazon.com/",
    "custom_terms_and_conditions": "Términos y condiciones",
    "phone_requirement": "none",
    "address_requirement": "none",
    "billing_info_requirement": "none",
    "prices": [
      {
        "id": "price_rky4dog7",
        "amount_in_cents": 500,
        "currency": "GTQ",
        "billing_interval_count": 0,
        "billing_interval": "",
        "charge_type": "one_time",
        "periods_before_automatic_cancellation": null,
        "free_trial_interval_count": 0,
        "free_trial_interval": ""
      }
    ],
    "storefront_link": "https://app.recurrente.com/s/surf-office/el-nombre-de-tu-producto-2",
    "metadata": {}
  }
]
```


### PATCH**Update a product**

**https://app.recurrente.com/api/products/{{productId}}**

Para actualizar el precio de un producto, debés pasar el parámetro de `<span>price_id</span>`, como se muestra en el ejemplo.

Adicional, puedes actualizar cualquier otro de los parámetros que se muestra en el endpoint de *Create a product.*

###### Borrar un precio

Para borrar un precio, adicional a pasar el `<span>price_id</span>` debés pasar el parámetro de `<span>_destroy</span>` como mostrado aquí:

`<span>product[prices_attributes][0][_destroy]</span>`

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Bodyformdata

**product[name]**

El nuevo nombre

El nombre del producto.

**product[prices_attributes[0][id]]**

{{priceId}}

Si quieres actualizar parámetros del precio, debés incluir el price_id

**product[prices_attributes[0][amount_in_cents]]**

1500

El monto a cobrar en centavos

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json

conn = http.client.HTTPSConnection("app.recurrente.com")
payload = json.dumps({
  "product": {
    "name": "El nuevo nombre del producto",
    "prices_attributes": [
      {
        "id": "price_mirvwr9y",
        "amount_in_cents": "1500"
      }
    ]
  }
})
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-Type': 'application/json'
}
conn.request("PATCH", "/api/products/{{productId}}", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**200 OK**

Example Response

* **Body**
* **Headers (0)**

View More

json

```json
{
  "id": "prod_wt1snpxg",
  "status": "active",
  "name": "El nuevo nombre del producto",
  "description": "Nuevos términos y condiciones",
  "success_url": "https://www.google.com/",
  "cancel_url": "https://www.amazon.com/",
  "custom_terms_and_conditions": "Nueva descripción",
  "phone_requirement": "none",
  "address_requirement": "none",
  "billing_info_requirement": "none",
  "prices": [
    {
      "id": "price_mirvwr9y",
      "amount_in_cents": 1500,
      "currency": "GTQ",
      "billing_interval_count": 1,
      "billing_interval": "month",
      "charge_type": "one_time",
      "periods_before_automatic_cancellation": null,
      "free_trial_interval_count": 0,
      "free_trial_interval": "month"
    }
  ],
  "storefront_link": "http://localhost:3000/s/surf-office/alquiler-de-tabla-por-el-dia",
  "metadata": {}
}
```

### DELETE**Delete a product**

**https://app.recurrente.com/api/products/{{productID}}**

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json
import mimetypes
from codecs import encode

conn = http.client.HTTPSConnection("app.recurrente.com")
boundary = ''
payload = ''
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-type': 'multipart/form-data; boundary={}'.format(boundary)
}
conn.request("DELETE", "/api/products/{{productId}}", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**200 OK**

Example Response

* **Body**
* **Headers (0)**

json

```json
{
  "id": "prod_m7vzucwi",
  "status": "deleted"
}
```



## Coupons

La API de Cupones permite a los comercios crear, consultar, actualizar y eliminar cupones de descuento.

Un cupón define una promoción que puede ser aplicada a un pago, por ejemplo un monto fijo de descuento o un porcentaje.

### POST**Create a coupon**

**https://app.recurrente.com/api/coupons**

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Bodyformdata

**coupon[name]**

VERANO25

El nombre de tu cupón

**coupon[amount_off_in_cents]**

1500

(Opcional) Monto de descuento en centavos (ej. 1500 = Q15.00)

**coupon[percent_off]**

10

(Opcional) Porcentaje de descuento (ej. 10 = 10%)

**coupon[currency]**

GTQ

Moneda ISO (ej. GTQ) – requerido si usas amount_off_in_cents

**coupon[duration]**

once | forever

En caso de una suscripción, si el cupón aplica solo al primer pago ("once") o a todos los pagos futuros ("forever").

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json

conn = http.client.HTTPSConnection("app.recurrente.com")
payload = json.dumps({
  "coupon": {
    "name": "NEWCOUPON",
    "amount_off_in_cents": 1500,
    "currency": "GTQ"
  }
})
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-Type': 'application/json'
}
conn.request("POST", "/api/coupons/", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**201 Created**

Example Response

* **Body**
* **Headers (0)**

json

```json
{
  "id": "coup_ugwoxcp4",
  "name": "NEWCOUPON",
  "amount_off_in_cents": 1500,
  "percent_off": null,
  "max_redemptions": null,
  "currency": "GTQ",
  "duration": "once",
  "expires_at": null,
  "status": "active"
}
```


### GET**Get a coupon**

**https://app.recurrente.com/api/coupons/{{couponId}}**

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json
import mimetypes
from codecs import encode

conn = http.client.HTTPSConnection("app.recurrente.com")
boundary = ''
payload = ''
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-type': 'multipart/form-data; boundary={}'.format(boundary)
}
conn.request("GET", "/api/coupons/{{couponID}}", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**200 OK**

Example Response

* **Body**
* **Headers (24)**

json

```json
{
  "id": "coup_ugwoxcp4",
  "name": "NEWCOUPON",
  "amount_off_in_cents": 1500,
  "percent_off": null,
  "max_redemptions": null,
  "currency": "GTQ",
  "duration": "once",
  "expires_at": null,
  "status": "active"
}
```



### GET**Get all coupons**

**https://app.recurrente.com/api/coupons**

Por defecto, se muestran los 10 cupones más recientes. Para obtener los siguientes 10 cupones, agrega query params.

Ejemplo: [https://app.recurrente.com/api/products?page=2](https://app.recurrente.com/api/subscriptions?page=2)

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json
import mimetypes
from codecs import encode

conn = http.client.HTTPSConnection("app.recurrente.com")
boundary = ''
payload = ''
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-type': 'multipart/form-data; boundary={}'.format(boundary)
}
conn.request("GET", "/api/coupons", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**200 OK**

Example Response

* **Body**
* **Headers (0)**

View More

json

```json
[
  {
    "id": "coup_ugwoxcp4",
    "name": "NEWCOUPON",
    "amount_off_in_cents": 1500,
    "percent_off": null,
    "max_redemptions": null,
    "currency": "GTQ",
    "duration": "once",
    "expires_at": null,
    "status": "active"
  }
]
```


### PATCH**Update a coupon**

**https://app.recurrente.com/api/coupons/{{couponId}}**

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Bodyformdata

**coupon[name]**

VERANO25

El nombre de tu cupón

**coupon[amount_off_in_cents]**

1500

(Opcional) Monto de descuento en centavos (ej. 1500 = Q15.00)

**coupon[percent_off]**

10

(Opcional) Porcentaje de descuento (ej. 10 = 10%)

**coupon[currency]**

GTQ

Moneda ISO (ej. GTQ) – requerido si usas amount_off_in_cents

**coupon[duration]**

once | forever

Duración del cupón

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json

conn = http.client.HTTPSConnection("app.recurrente.com")
payload = json.dumps({
  "coupon": {
    "name": "NEWCOUPON",
    "amount_off_in_cents": 1500,
    "currency": "GTQ"
  }
})
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-Type': 'application/json'
}
conn.request("POST", "/api/coupons/{{couponID}}", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**201 Created**

Example Response

* **Body**
* **Headers (0)**

json

```json
{
  "id": "coup_ugwoxcp4",
  "name": "NEWCOUPON",
  "amount_off_in_cents": 1500,
  "percent_off": null,
  "max_redemptions": null,
  "currency": "GTQ",
  "duration": "once",
  "expires_at": null,
  "status": "active"
}
```



### DELETE**Delete a coupon**

**https://app.recurrente.com/api/coupons/{{couponID}}**

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json
import mimetypes
from codecs import encode

conn = http.client.HTTPSConnection("app.recurrente.com")
boundary = ''
payload = ''
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-type': 'multipart/form-data; boundary={}'.format(boundary)
}
conn.request("DELETE", "/api/coupons/{{couponID}}", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**200 OK**

Example Response

* **Body**
* **Headers (0)**

json

```json
{
  "id": "coup_eug4euns",
  "status": "deleted"
}
```



## Subscriptions

Las suscripciones te permiten crear pagos recurrentes. Puedes cobrar semanal, mensual, o anualmente. O puedes elegir un período más específico, como "cada 2 meses". Una vez el usuario empiece su suscripción, se le cobrará recurrentemente en el intervalo seleccionado.

###### Status de una suscripción

Los posibles status de una suscripción son:

* `<span>active</span>` - Cuando la suscripción está activa y los pagos están al día.
* `<span>paused</span>` - Cuando la suscripción fue pausada, ya sea por el comercio o por el usuario. La suscripción no se cobrará de nuevo hasta que el estado sea cambiado a `<span>active</span>`
* `<span>past_due</span>` - Cuando el período de la suscripción está vencido y no se ha logrado cobrar el último pago. Se hacen 3 re-intentos automáticos de cobrar el pago en los siguientes 5 días. Si se logra cobrar, se cambia a un estado de `<span>active</span>`. Si no se logra cobrar, se cambia a `<span>cancelled</span>`.
* `<span>cancelled</span>` - Cuando la suscripción fue cancelada. Ya no se harán intentos de cobro.
* `<span>unable_to_start</span>` - Cuando el primer pago de la suscripción es fallido y no es posible activar la suscripción.

### GET**Get a subscription**

**https://app.recurrente.com/api/subscriptions/{{subscriptionId}}**

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json
import mimetypes
from codecs import encode

conn = http.client.HTTPSConnection("app.recurrente.com")
boundary = ''
payload = ''
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-type': 'multipart/form-data; boundary={}'.format(boundary)
}
conn.request("GET", "/api/subscriptions/{{subscriptionId}}", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**200 OK**

Example Response

* **Body**
* **Headers (0)**

View More

json

```json
{
  "id": "su_nehndm7j",
  "description": "One Free-Testable Banana",
  "status": "active",
  "created_at": "2024-03-01T03:52:12.636-06:00",
  "updated_at": "2024-03-01T03:52:12.982-06:00",
  "current_period_start": "2024-03-01T03:52:12.636-06:00",
  "current_period_end": "2024-03-02T03:52:12.636-06:00",
  "tax_name": null,
  "tax_id": null,
  "subscriber": {
    "id": "us_rdctav2g",
    "first_name": "Fela",
    "last_name": "Kuti",
    "full_name": "Fela Kuti",
    "email": "test@user.com",
    "phone_number": null
  },
  "checkout": {
    "id": "ch_lmgbvesmihkqzma3"
  },
  "product": {
    "id": "pr_7ehozftv"
  }
}
```

### GET**Get all subscriptions**

**https://app.recurrente.com/api/subscriptions**

Por defecto, se muestran las 10 suscripciones más recientes. Para obtener las siguientes 10 suscripciones, agrega query params.

Ejemplo: [https://app.recurrente.com/api/subscriptions?page=2](https://app.recurrente.com/api/subscriptions?page=2)

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json
import mimetypes
from codecs import encode

conn = http.client.HTTPSConnection("app.recurrente.com")
boundary = ''
payload = ''
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-type': 'multipart/form-data; boundary={}'.format(boundary)
}
conn.request("GET", "/api/subscriptions", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**200 OK**

Example Response

* **Body**
* **Headers (0)**

View More

json

```json
[
  {
    "id": "su_nehndm7j",
    "description": "One Free-Testable Banana",
    "status": "active",
    "created_at": "2024-03-01T03:52:12.636-06:00",
    "updated_at": "2024-03-01T03:52:12.982-06:00",
    "current_period_start": "2024-03-01T03:52:12.636-06:00",
    "current_period_end": "2024-03-02T03:52:12.636-06:00",
    "tax_name": null,
    "tax_id": null,
    "subscriber": {
      "id": "us_rdctav2g",
      "first_name": "Fela",
      "last_name": "Kuti",
      "full_name": "Fela Kuti",
      "email": "test@user.com",
      "phone_number": null
    },
    "checkout": {
      "id": "ch_lmgbvesmihkqzma3"
    },
    "product": {
      "id": "pr_7ehozftv"
    }
  }
]
```


### DELETE**Cancel a subscription**

**https://app.recurrente.com/api/subscriptions/{{subscriptionId}}**

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json
import mimetypes
from codecs import encode

conn = http.client.HTTPSConnection("app.recurrente.com")
boundary = ''
payload = ''
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-type': 'multipart/form-data; boundary={}'.format(boundary)
}
conn.request("DELETE", "/api/subscriptions/{{subscriptionId}}", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**200 OK**

Example Response

* **Body**
* **Headers (0)**

json

```json
{
  "message": "Suscripción cancelada"
}
```



## Users

### POST**Create a user**

**https://app.recurrente.com/api/users/**

Existen dos formas de crear un checkout. Aquí, vamos a ver la primera:

* **Pasando todos los detalles (nombre, precio, etc.) de los "items" que quiero añadir.**
* Pasando el "Price ID" de los productos que quiero añadir.

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Bodyformdata

**email**

me@example.com

**full_name**

Jorge Luis Borges

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json

conn = http.client.HTTPSConnection("app.recurrente.com")
payload = json.dumps({
  "email": "me@example.com",
  "full_name": "Jorge Luis Borges"
})
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-Type': 'application/json'
}
conn.request("POST", "/api/users/", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**200 OK**

Example Response

* **Body**
* **Headers (0)**

json

```json
{
  "email": "me@example.com",
  "id": "us_y6fxiihb"
}
```


POST**Create a transfer**

**https://app.recurrente.com/api/transfers/**

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Bodyformdata

**currency**

GTQ

La moneda a cobrar. Posibles valores son:

* GTQ
* USD

**amount_in_cents**

100

El monto a cobrar en centavos

**recipient_id**

recurrente

El recipient_id es el @ de la cuenta a la que quieres enviar dinero.

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json

conn = http.client.HTTPSConnection("app.recurrente.com")
payload = json.dumps({
  "currency": "GTQ",
  "amount_in_cents": "100",
  "recipient_id": "recurrente"
})
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-Type': 'application/json'
}
conn.request("POST", "/api/transfers/", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**200 OK**

Example Response

* **Body**
* **Headers (0)**

json

```json
{
  "id": "tr_nr4yplup",
  "status": "completed"
}
```



## Refunds

### POST**Create a refund**

**https://app.recurrente.com/api/refunds/**

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Bodyformdata

**payment_intent_id**

pa_abc123

El ID del pago que se desea reembolsar

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json

conn = http.client.HTTPSConnection("app.recurrente.com")
payload = json.dumps({
  "payment_intent_id": "pa_e6kc6vx2"
})
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-Type': 'application/json'
}
conn.request("POST", "/api/refunds/", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**200 OK**

Example Response

* **Body**
* **Headers (0)**

View More

json

```json
{
  "id": "re_3jfrywsf",
  "status": "succeeded",
  "customer": {
    "id": "us_ik1qykpd",
    "email": "juan@gmail.com",
    "full_name": "Juan Perez"
  },
  "account_refunded_amount_in_cents": 2187,
  "customer_refunded_amount_in_cents": 2500,
  "currency": "GTQ",
  "created_at": "2024-06-23T12:26:51.962-06:00"
}
```


### GET**Get a refund**

**https://app.recurrente.com/api/refunds/{{refundId}}**

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json

conn = http.client.HTTPSConnection("app.recurrente.com")
payload = ''
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-Type': 'application/json'
}
conn.request("GET", "/api/refunds/{{refundId}}", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**200 OK**

Example Response

* **Body**
* **Headers (0)**

View More

json

```json
{
  "id": "re_3jfrywsf",
  "status": "succeeded",
  "customer": {
    "id": "us_ik1qykpd",
    "email": "juan@gmail.com",
    "full_name": "Juan Perez"
  },
  "account_refunded_amount_in_cents": 2187,
  "customer_refunded_amount_in_cents": 2500,
  "currency": "GTQ",
  "created_at": "2024-06-23T12:26:51.962-06:00"
}
```


## Webhooks

###### Instalación

Para activar webhooks para tu cuenta, dentro de tu cuenta de Recurrente, ve a:

**Configuración** → **Desarrolladores y API.**

Ahí apacha en **"Webhooks",** y continúa a añadir el *endpoint* a donde quieres que sean enviados los requests.

###### Webhook Event Types

**payment_intent.succeeded**

Se emite con un cobro exitoso con tarjeta (crédito o débito). Los fondos ya están en tu balance de Recurrente.

*Ejemplo de respuesta:*

View More

json

```json
{
  "id": "pa_id123",
  "event_type": "payment_intent.succeeded",
  "api_version": "2024-04-24",
  "checkout": {
    "id": "ch_id123",
    "status": "paid",
    "payment": {
      "id": "pa_laybj3zw",
      "paymentable": {
        "type": "OneTimePayment",
        "id": "on_arognqni",
        "tax_name": null,
        "tax_id": null,
        "address": null,
        "phone_number": null
      }
    },
    "payment_method": {
      "id": "pay_m_7v5ie3pw",
      "type": "card",
      "card": {
        "last4": "0000",
        "network": "visa"
      }
    },
    "transfer_setups": [],
    "metadata": {}
  },
  "created_at": "2024-02-16T03:01:13.260Z",
  "failure_reason": null,
  "amount_in_cents": 10000,
  "currency": "GTQ",
  "fee": 450,
  "vat_withheld": 160,
  "vat_withheld_currency": "GTQ",
  "customer": {
    "email": "hello@example.com",
    "full_name": "Max Rodriguez",
    "id": "us_id123"
  },
  "payment": {
    "id": "pa_id123",
    "paymentable": {
      "id": "su_id123",
      "tax_id": null,
      "tax_name": null,
      "type": "Subscription",
      "address": {
        "address_line_1": "Plaza Obelisco",
        "address_line_2": null,
        "city": "Guatemala",
        "country": "Guatemala",
        "zip_code": "01010"
      },
      "phone_number": "5555-5555"
    }
  },
  "product": {
    "id": "prod_id123"
  },
  "invoice": {
    "id": "inv_123",
    "tax_invoice_url": null
  }
}
```

**payment_intent.failed**

Cobro fallido con tarjeta.

*Ejemplo de respuesta:*

View More

json

```json
{{
  "id": "pa_id123",
  "event_type": "payment_intent.failed",
  "api_version": "2024-03-13",
  "checkout": {
    "id": "ch_id123"
  },
  "created_at": "2024-02-16T03:01:13.260Z",
  "failure_reason": "Tu banco ha rechazado la transacción. Llama a tu banco y pide que autoricen esta transacción.",,
  "amount_in_cents": 10000,
  "currency": "GTQ",
  "fee": 0,
  "vat_withheld": 0,
  "vat_withheld_currency": "GTQ",
  "customer": {
    "email": "hello@example.com",
    "full_name": "Max Rodriguez",
    "id": "us_id123"
  },
  "payment": {
    "id": "pa_id123",
    "paymentable": {
      "id": "su_id123",
      "tax_id": null,
      "tax_name": null,
      "type": "Subscription",
      "address": {
        "address_line_1": "Plaza Obelisco",
        "address_line_2": null,
        "city": "Guatemala",
        "country": "Guatemala",
        "zip_code": "01010"
      },
      "phone_number": "5555-5555"
    }
  },
  "product": {
    "id": "prod_id123"
  },
  "invoice": {
    "id": "inv_123",
    "tax_invoice_url": null
  }
}
```

**subscription.create**

Si el producto es recurrente, se emite además del payment.succeeded este evento con la información de la suscripción.

*Ejemplo de respuesta:*

View More

json

```json
{
  "api_version": "2024-04-24",
  "created_at": "2025-10-13T13:59:27.931Z",
  "customer_email": "example@example.com",
  "customer_id": "us_1234",
  "customer_name": "Pedro Pérez",
  "event_type": "subscription.create",
  "id": "su_123",
  "payment": {
    "id": "pa_123",
    "paymentable": {
      "address": null,
      "id": "su_123",
      "phone_number": "+50255555555",
      "tax_id": "",
      "tax_name": null,
      "type": "Subscription"
    }
  },
  "product": {
    "address_requirement": "none",
    "billing_info_requirement": "optional",
    "cancel_url": "",
    "custom_terms_and_conditions": "Términos y condiciones",
    "description": "Suscripción de prueba",
    "has_dynamic_pricing": false,
    "id": "prod_123",
    "metadata": {},
    "name": "Plan de Prueba",
    "phone_requirement": "required",
    "prices": [
      {
        "amount_in_cents": 999,
        "billing_interval": "month",
        "billing_interval_count": 1,
        "charge_type": "recurring",
        "currency": "GTQ",
        "free_trial_interval": "month",
        "free_trial_interval_count": 0,
        "id": "price_123",
        "periods_before_automatic_cancellation": null
      }
    ],
    "status": "active",
    "storefront_link": "https://app.recurrente.com/s/recurrente/plan-de-prueba",
    "success_url": ""
  }
}
```

**subscription.past_due**

Se emite cuando el cobro automático de una suscripción falla por primera vez.

*Nota: En una suscripción, cuando un pago falla, Recurrente intenta cobrarlo de nuevo 3 y 5 días después. Si ambos re-intentos son fallidos, en ese momento se cancela la suscripción.*

*Ejemplo de respuesta:*

View More

json

```json
{
  "api_version": "2024-04-24",
  "created_at": "2025-10-13T13:59:27.931Z",
  "customer_email": "example@example.com",
  "customer_id": "us_1234",
  "customer_name": "Pedro Pérez",
  "event_type": "subscription.past_due",
  "id": "su_123",
  "payment": {
    "id": "pa_123",
    "paymentable": {
      "address": null,
      "id": "su_123",
      "phone_number": "+50255555555",
      "tax_id": "",
      "tax_name": null,
      "type": "Subscription"
    }
  },
  "product": {
    "address_requirement": "none",
    "billing_info_requirement": "optional",
    "cancel_url": "",
    "custom_terms_and_conditions": "Términos y condiciones",
    "description": "Suscripción de prueba",
    "has_dynamic_pricing": false,
    "id": "prod_123",
    "metadata": {},
    "name": "Plan de Prueba",
    "phone_requirement": "required",
    "prices": [
      {
        "amount_in_cents": 999,
        "billing_interval": "month",
        "billing_interval_count": 1,
        "charge_type": "recurring",
        "currency": "GTQ",
        "free_trial_interval": "month",
        "free_trial_interval_count": 0,
        "id": "price_123",
        "periods_before_automatic_cancellation": null
      }
    ],
    "status": "active",
    "storefront_link": "https://app.recurrente.com/s/recurrente/plan-de-prueba",
    "success_url": ""
  }
}
```

**subscription.paused**

Se emite cuando se pausa la suscripción. Una suscripción pausada no se volverá a cobrar hasta que sea reactivada.

*Ejemplo de respuesta:*

View More

json

```json
{
  "api_version": "2024-04-24",
  "created_at": "2025-10-13T13:59:27.931Z",
  "customer_email": "example@example.com",
  "customer_id": "us_1234",
  "customer_name": "Pedro Pérez",
  "event_type": "subscription.paused",
  "id": "su_123",
  "payment": {
    "id": "pa_123",
    "paymentable": {
      "address": null,
      "id": "su_123",
      "phone_number": "+50255555555",
      "tax_id": "",
      "tax_name": null,
      "type": "Subscription"
    }
  },
  "product": {
    "address_requirement": "none",
    "billing_info_requirement": "optional",
    "cancel_url": "",
    "custom_terms_and_conditions": "Términos y condiciones",
    "description": "Suscripción de prueba",
    "has_dynamic_pricing": false,
    "id": "prod_123",
    "metadata": {},
    "name": "Plan de Prueba",
    "phone_requirement": "required",
    "prices": [
      {
        "amount_in_cents": 999,
        "billing_interval": "month",
        "billing_interval_count": 1,
        "charge_type": "recurring",
        "currency": "GTQ",
        "free_trial_interval": "month",
        "free_trial_interval_count": 0,
        "id": "price_123",
        "periods_before_automatic_cancellation": null
      }
    ],
    "status": "active",
    "storefront_link": "https://app.recurrente.com/s/recurrente/plan-de-prueba",
    "success_url": ""
  }
}
```

**subscription.cancel**

Se emite cuando el cobro automático de una suscripción falla por tercera vez.

*Nota: En una suscripción, cuando un pago falla, Recurrente intenta cobrarlo de nuevo 3 y 5 días después. Si ambos re-intentos son fallidos, en ese momento se cancela la suscripción.*

*Ejemplo de respuesta:*

View More

json

```json
{
  "api_version": "2024-04-24",
  "created_at": "2025-10-13T13:59:27.931Z",
  "customer_email": "example@example.com",
  "customer_id": "us_1234",
  "customer_name": "Pedro Pérez",
  "event_type": "subscription.cancel",
  "id": "su_123",
  "payment": {
    "id": "pa_123",
    "paymentable": {
      "address": null,
      "id": "su_123",
      "phone_number": "+50255555555",
      "tax_id": "",
      "tax_name": null,
      "type": "Subscription"
    }
  },
  "product": {
    "address_requirement": "none",
    "billing_info_requirement": "optional",
    "cancel_url": "",
    "custom_terms_and_conditions": "Términos y condiciones",
    "description": "Suscripción de prueba",
    "has_dynamic_pricing": false,
    "id": "prod_123",
    "metadata": {},
    "name": "Plan de Prueba",
    "phone_requirement": "required",
    "prices": [
      {
        "amount_in_cents": 999,
        "billing_interval": "month",
        "billing_interval_count": 1,
        "charge_type": "recurring",
        "currency": "GTQ",
        "free_trial_interval": "month",
        "free_trial_interval_count": 0,
        "id": "price_123",
        "periods_before_automatic_cancellation": null
      }
    ],
    "status": "active",
    "storefront_link": "https://app.recurrente.com/s/recurrente/plan-de-prueba",
    "success_url": ""
  }
}
```

**bank_transfer_intent.pending**

Se emite cuando se inicia un cobro con transferencia bancaria. En cuanto se reciba el dinero en la cuenta, se emitirá bank_transfer_intent.succeeded. De lo contrario, se emitirá bank_transfer_intent.failed.

View More

json

```json
{
   "id":"ba_123",
   "event_type": "bank_transfer_intent.pending",
   "api_version": "2024-04-24",
   "created_at":"2024-03-04T18:08:40.210Z",
   "customer_id": "us_t8nlvpwq",
  "customer": {
    "id": "us_t8nlvpwq"
  },
  "amount_in_cents": 10000,
  "currency": "GTQ",
   "product": {
      "id":"prod_123"
   },
  "checkout": {
    "id": "ch_5wlclm4jqpg3fe09",
    "status": "payment_in_progress",
    "payment": {
      "id": "pa_123",
      "paymentable": {
        "type": "OneTimePayment",
        "id": "on_123",
        "tax_name": "Acme S.A.",
        "tax_id": "1234567",
        "address": {
          "address_line_1": "Plaza Obelisco",
          "address_line_2": null,
          "city": "Guatemala",
          "country": "Guatemala",
          "zip_code": "01010"
        },
        "phone_number": "5555-5555"
      }
   },
    "payment_method": null,
    "transfer_setups": [],
    "metadata": {}
  },
   "payment": {
      "id": "pa_123",
      "paymentable": {
        "type": "OneTimePayment", // Deprecated, no usar
        "id": "on_123", // Deprecated, no usar
        "tax_name": "Acme S.A.",
        "tax_id": "1234567",
        "address": {
          "address_line_1": "Plaza Obelisco",
          "address_line_2": null,
          "city": "Guatemala",
          "country": "Guatemala",
          "zip_code": "01010"
        },
        "phone_number": "5555-5555"
      }
   },
  "tax_invoice_url": null
}
```

**bank_transfer_intent.succeeded**

Se emite con un cobro exitoso con transferencia bancaria. Los fondos ya están en tu balance de Recurrente.

View More

json

```json
{
   "id":"ba_123",
   "event_type": "bank_transfer_intent.succeeded",
   "api_version": "2024-04-24",
   "created_at":"2024-03-04T18:08:40.210Z",
   "customer_id": "us_t8nlvpwq",
  "customer": {
    "id": "us_t8nlvpwq"
  },
  "amount_in_cents": 10000,
  "currency": "GTQ",
   "product": {
      "id":"prod_123"
   },
   "checkout": {
    "id": "ch_5wlclm4jqpg3fe09",
    "status": "paid",
    "payment": {
      "id": "pa_123",
      "paymentable": {
        "type": "OneTimePayment",
        "id": "on_123",
        "tax_name": "Acme S.A.",
        "tax_id": "1234567",
        "address": {
          "address_line_1": "Plaza Obelisco",
          "address_line_2": null,
          "city": "Guatemala",
          "country": "Guatemala",
          "zip_code": "01010"
        },
        "phone_number": "5555-5555"
      }
   },
    "payment_method": {
      "id": "pay_m_zmbxckyn",
      "type": "bank_transfer_receiver",
      "bank_transfer_receiver": {}
    },
    "transfer_setups": [],
    "metadata": {}
  },
  "payment": {
      "id": "pa_123",
      "paymentable": {
        "type": "OneTimePayment", // Deprecated, no usar
        "id": "on_123", // Deprecated, no usar
        "tax_name": "Acme S.A.",
        "tax_id": "1234567",
        "address": {
          "address_line_1": "Plaza Obelisco",
          "address_line_2": null,
          "city": "Guatemala",
          "country": "Guatemala",
          "zip_code": "01010"
        },
        "phone_number": "5555-5555"
      }
   },
  "tax_invoice_url": null
}
```

**bank_transfer_intent.failed**

Se emite con un cobro fallido con transferencia bancaria. Esto sucede cuando no se reciben los fondos en la cuenta de banco, o se recibe el monto incorrecto.

View More

json

```json
{
   "id":"ba_123",
   "event_type": "bank_transfer_intent.failed",
   "api_version":"2023-08-29",
   "created_at":"2024-03-04T18:08:40.210Z",
   "customer_id": "us_t8nlvpwq",
  "customer": {
    "id": "us_t8nlvpwq"
  },
  "amount_in_cents": 10000,
  "currency": "GTQ",
   "product": {
      "id":"prod_123"
   },
   "checkout": {
    "id": "ch_5wlclm4jqpg3fe09",
    "status": "unpaid",
    "payment": {
      "id": "pa_123",
      "paymentable": {
        "type": "OneTimePayment",
        "id": "on_123",
        "tax_name": "Acme S.A.",
        "tax_id": "1234567",
        "address": {
          "address_line_1": "Plaza Obelisco",
          "address_line_2": null,
          "city": "Guatemala",
          "country": "Guatemala",
          "zip_code": "01010"
        },
        "phone_number": "5555-5555"
      }
   },
    "payment_method": null,
    "transfer_setups": [],
    "metadata": {}
  },
   "payment": {
      "id": "pa_123",
      "paymentable": {
        "type": "OneTimePayment", // Deprecated, no usar
        "id": "on_123", // Deprecated, no usar
        "tax_name": "Acme S.A.",
        "tax_id": "1234567",
        "address": {
          "address_line_1": "Plaza Obelisco",
          "address_line_2": null,
          "city": "Guatemala",
          "country": "Guatemala",
          "zip_code": "01010"
        },
        "phone_number": "5555-5555"
      }
   },
  "tax_invoice_url": null
}
```

**setup_intent.succeeded**

Se emite cuando se inicia exitosamente una suscripción con un período de prueba. También se emite cuando se tokeniza una tarjeta sin cobrarla.

json

```json
{
   "api_version":"2024-03-13",
   "created_at":"2024-04-10T10:31:45.806-06:00",
   "event_type":"setup_intent.succeeded",
   "status":"succeeded",
   "suscription":{
      "id":"su_vh8v33ac"
   }
}
```

**setup_intent.cancelled**

Se emite cuando no se logra tokenizar una tarjeta sin cobrarla. Esto sucede cuando el primer pago de una suscripción con período de prueba, falla.

json

```json
{
   "api_version":"2024-03-13",
   "created_at":"2024-04-10T10:31:45.806-06:00",
   "event_type":"setup_intent.cancelled",
   "status":"cancelled",
   "suscription":{
      "id":"su_vh8v33ac"
   }
}
```



### POST**Create a webhook endpoint**

**https://app.recurrente.com/api/webhook_endpoints/**

# Create Webhook Endpoint

Permite crear nuevos webhooks endpoints en donde se enviaran las notificaciones webhook.

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Bodyformdata

**url**

https://example.com/webhook

El url al que se enviarán los webhooks

**description**

Mi endpoint de prueba

Opcional. Una breve descripción del endpoint

**metadata**

{}

Opcional. Cualquier información que quieras adjuntar al endpoint

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json

conn = http.client.HTTPSConnection("app.recurrente.com")
payload = json.dumps({
  "url": "https://example.com/webhook",
  "description": "Optional description of the endpoint",
  "metadata": {}
})
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-Type': 'application/json'
}
conn.request("POST", "/api/webhook_endpoints/", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**200 OK**

Example Response

* **Body**
* **Headers (0)**

json

```json
{
  "description": "Optional description of the endpoint",
  "url": "https://example.com/webhook",
  "disabled": false,
  "createdAt": "2024-05-03T18:28:07.673413Z",
  "updatedAt": "2024-05-03T18:28:07.673427Z",
  "id": "ep_2fy6I9KODnHzw7Zf0ZGmMs8gEN9",
  "metadata": {}
}
```



### DELETE**Delete a webhook endpoint**

**https://app.recurrente.com/api/webhook_endpoints/{{webhookId}}**

# Create Webhook Endpoint

This endpoint allows you to create a new webhook endpoint for receiving webhook notifications.

## Request Body

* `<span>url</span>` (text): The URL to which the webhook notifications will be sent.
* `<span>description</span>` (text, optional): A brief description of the endpoint.
* `<span>metadata</span>` (text, optional): Any additional information you want to attach to the endpoint.

### Example

json

```json
{
    "url": "https://your-webhook-url.com",
    "description": "Optional description of the endpoint",
    "metadata": "Optional metadata"
}
```

## Response

* `<span>id</span>` (string): The ID of the created webhook endpoint.
* `<span>status</span>` (string): The status of the request.

### Example

json

```json
{
    "id": "webhook_endpoint_id",
    "status": "success"
}
```

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json

conn = http.client.HTTPSConnection("app.recurrente.com")
payload = ''
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}'
}
conn.request("DELETE", "/api/webhook_endpoints/{{webhookId}}", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**200 OK**

Example Response

* **Body**
* **Headers (0)**

json

```json
{
  "description": "Optional description of the endpoint",
  "url": "https://example.com/webhook",
  "disabled": false,
  "createdAt": "2024-05-03T18:28:07.673413Z",
  "updatedAt": "2024-05-03T18:28:07.673427Z",
  "id": "ep_2fy6I9KODnHzw7Zf0ZGmMs8gEN9",
  "metadata": {}
}
```



### GET**Get all webhook endpoints**

**https://app.recurrente.com/api/webhook_endpoints/**

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json

conn = http.client.HTTPSConnection("app.recurrente.com")
payload = ''
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}'
}
conn.request("GET", "/api/webhook_endpoints/", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**200 OK**

Example Response

* **Body**
* **Headers (0)**

json

```json
[
  {
    "description": "Optional description of the endpoint",
    "url": "https://example.com/webhook",
    "disabled": false,
    "createdAt": "2024-05-03T18:28:07.673413Z",
    "updatedAt": "2024-05-03T18:28:07.673427Z",
    "id": "ep_2fy6I9KODnHzw7Zf0ZGmMs8gEN9",
    "metadata": {}
  }
]
```



## Cuentas Conectadas

Si estás construyendo una plataforma o un marketplace, y quieres:

* Cobrar en nombre de alguien más o;
* Compartir los ingresos de las ventas con otras cuentas

La funcionalidad de "Cuentas conectadas" es para ti.

👨‍💻 Con Cuentas Conectadas puedes  **realizar cobros en nombre de otras cuentas utilizando tus propias Llaves API** , sin necesidad de acceder ni utilizar las llaves API de esas cuentas.

###### ¿Cómo conecto dos cuentas?

Esto se debe hacer a través del UI de Recurrente. Sigue [las intrucciones aquí](https://ayuda.recurrente.com/es/articles/9185861-cuentas-conectadas-como-cobrar-en-nombre-de-otra-cuenta).

###### ¿Cómo me entero de los eventos en una cuenta hija?

A través de Webhooks, recibirás eventos con los parámetros `<span>connected: true</span>` y `<span>account_id: ac_123456</span>` con lo que podrás identificar el evento y la cuenta que lo generó.

### POST**Create a checkout for a connected account**

**https://app.recurrente.com/api/checkouts/**

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

PARAMS

Bodyformdata

**items[][currency]**

GTQ

La moneda a cobrar.

Posibles valores son:

* GTQ
* USD

**items[][amount_in_cents]**

3000

Monto a cobrar en centavos.

**custom_account_id**

ac_123456

(Opcional) El ID de la cuenta que va a crear el checkout. Debe ser una cuenta conectada (hija).

Si lo dejas en blanco, sera tu cuenta quien creará el checkout.

**transfer_setups[][amount_in_cents]**

100

(Opcional) Monto en centavos a enviar a otra cuenta después de un pago exitoso.

**transfer_setups[][recipient_id]**

(Opcional) El ID de la cuenta a la cuál se va a enviar el monto definido anteriormente al recibir un pago exitoso. Puede ser cualquier cuenta de Recurrente.

Si se queda en blanco, se usará el ID de tu cuenta como default, y el monto en centavos se te transferirá a ti.

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json
import mimetypes
from codecs import encode

conn = http.client.HTTPSConnection("app.recurrente.com")
dataList = []
boundary = 'wL36Yn8afVp8Ag7AmP8qZ0SA4n1v9T'
dataList.append(encode('--' + boundary))
dataList.append(encode('Content-Disposition: form-data; name=items[][currency];'))

dataList.append(encode('Content-Type: {}'.format('text/plain')))
dataList.append(encode(''))

dataList.append(encode("GTQ"))
dataList.append(encode('--' + boundary))
dataList.append(encode('Content-Disposition: form-data; name=items[][amount_in_cents];'))

dataList.append(encode('Content-Type: {}'.format('text/plain')))
dataList.append(encode(''))

dataList.append(encode("3000"))
dataList.append(encode('--' + boundary))
dataList.append(encode('Content-Disposition: form-data; name=custom_account_id;'))

dataList.append(encode('Content-Type: {}'.format('text/plain')))
dataList.append(encode(''))

dataList.append(encode("ac_123456"))
dataList.append(encode('--' + boundary))
dataList.append(encode('Content-Disposition: form-data; name=transfer_setups[][amount_in_cents];'))

dataList.append(encode('Content-Type: {}'.format('text/plain')))
dataList.append(encode(''))

dataList.append(encode("100"))
dataList.append(encode('--' + boundary))
dataList.append(encode('Content-Disposition: form-data; name=transfer_setups[][recipient_id];'))

dataList.append(encode('Content-Type: {}'.format('text/plain')))
dataList.append(encode(''))

dataList.append(encode(""))
dataList.append(encode('--'+boundary+'--'))
dataList.append(encode(''))
body = b'\r\n'.join(dataList)
payload = body
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-type': 'multipart/form-data; boundary={}'.format(boundary)
}
conn.request("POST", "/api/checkouts/", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**201 Created**

Example Response

* **Body**
* **Headers (0)**

json

```json
{
  "id": "ch_672wumotzeuqqyzf",
  "checkout_url": "https://app.recurrente.com/checkout-session/ch_672wumotzeuqqyzf"
}
```



## Embedded Checkouts

**Para ver la versión más actualizada de esta guía, visita el repo:** [https://github.com/recurrente/recurrente-checkout](https://github.com/recurrente/recurrente-checkout)

**Recurrente Checkout** es una librería JavaScript que te permite  **insertar un checkout responsivo y seguro en tu propia página web** . Funciona mostrando un iframe con tu sesión de pago y maneja callbacks para eventos clave como éxito, fallo o pagos en proceso.

Para ver un video de cómo funciona: [https://youtu.be/OUIYVcrnPr0](https://youtu.be/OUIYVcrnPr0)

 **Antes de comenzar** : Para usar esta biblioteca, necesitas crear un checkout en Recurrente. Consulta la [documentación de creación de checkouts](https://docs.recurrente.com/) para obtener tu URL de checkout.

## Instalación

## NPM (Recomendado)

Plain Text

```plain
npm install recurrente-checkout
```

### CDN

⚠️ En producción, recomendamos usar una versión específica (por ejemplo, @0.0.4) en lugar de @latest, para evitar romper integraciones al actualizar automáticamente.

#### Unpkg

Plain Text

```plain
<script src="https://unpkg.com/recurrente-checkout@latest/recurrente-checkout.js"></script>
```

#### jsDelivr

Plain Text

```plain
<script src="https://cdn.jsdelivr.net/npm/recurrente-checkout@latest/recurrente-checkout.js"></script>
```

¿Dónde aparece el checkout?

El checkout de Recurrente se renderiza como un iframe que se inserta automáticamente en el elemento HTML con el ID `<span>recurrente-checkout-container</span>`. Asegúrate de tener este elemento en tu página:

View More

html

```html
<div class='preserveHtml' class='preserveHtml' class='preserveHtml' class='preserveHtml' class='preserveHtml' class='preserveHtml' id="recurrente-checkout-container"></div>
```

El iframe se ajustará automáticamente al tamaño del contenedor y será responsive. Puedes personalizar la apariencia aplicando estilos CSS al contenedor.

### ES6 Modules (Recomendado)

View More

javascript

```javascript
import RecurrenteCheckout from 'recurrente-checkout';
RecurrenteCheckout.load({
  url: "https://app.recurrente.com/checkout-session/ch_1234",
  onSuccess: function(paymentData) {
    console.log('Pago exitoso:', paymentData);
    // Manejar pago exitoso
    // ej., redirigir a página de éxito, actualizar UI, etc.
  },
  onFailure: function(error) {
    console.log('Pago fallido:', error);
    // Manejar pago fallido
    // ej., mostrar mensaje de error, opción de reintentar, etc.
  },
  onPaymentInProgress: function() {
    console.log('Pago con transferencia bancaria en proceso');
    // Este callback se ejecuta solo para transferencias bancarias
    // El pago puede tomar hasta 24 horas en procesarse
    // ej., mostrar mensaje informativo, enviar email de confirmación, etc.
  }
});
```

### Importación Nominal

View More

javascript

```javascript
import { loadRecurrenteCheckout } from 'recurrente-checkout';
loadRecurrenteCheckout({
  url: "https://app.recurrente.com/checkout-session/ch_1234",
  onSuccess: function(paymentData) {
    console.log('Pago exitoso:', paymentData);
  },
  onFailure: function(error) {
    console.log('Pago fallido:', error);
  },
  onPaymentInProgress: function() {
    console.log('Pago con transferencia bancaria en proceso');
    // Solo para transferencias bancarias (puede tomar hasta 24h)
  }
});
```

### CommonJS

View More

javascript

```javascript
const RecurrenteCheckout = require('recurrente-checkout');
RecurrenteCheckout.load({
  url: "https://app.recurrente.com/checkout-session/ch_1234",
  onSuccess: function(paymentData) {
    console.log('Pago exitoso:', paymentData);
  },
  onFailure: function(error) {
    console.log('Pago fallido:', error);
  },
  onPaymentInProgress: function() {
    console.log('Pago con transferencia bancaria en proceso');
    // Solo para transferencias bancarias (puede tomar hasta 24h)
  }
});
```

### Navegador (Global)

View More

javascript

```javascript
<script src="https://unpkg.com/recurrente-checkout@latest/recurrente-checkout.js"></script>
<script>
  RecurrenteCheckout.load({
    url: "https://app.recurrente.com/s/your-checkout-url",
    onSuccess: function(paymentData) {
      console.log('Pago exitoso:', paymentData);
    },
    onFailure: function(error) {
      console.log('Pago fallido:', error);
    },
    onPaymentInProgress: function() {
      console.log('Pago con transferencia bancaria en proceso');
      // Solo para transferencias bancarias (puede tomar hasta 24h)
    }
  });
</script>
```

## Integración Rápida

### 1. Incluir la Biblioteca JavaScript

Elige uno de los métodos de instalación anteriores.

### 2. Inicializar el Checkout

Elige uno de los dos métodos de integración:

#### Método A: URL de Checkout Directa

View More

javascript

```javascript
RecurrenteCheckout.load({
  url: "https://app.recurrente.com/checkout-session/ch_1234",
  onSuccess: function(paymentData) {
    console.log('Pago exitoso:', paymentData.checkoutId);
    // Manejar pago exitoso
    // ej., redirigir a página de éxito, actualizar UI, etc.
  },
  onFailure: function(data) {
    console.log('Pago fallido:', data.error);
    // Manejar pago fallido
    // ej., mostrar mensaje de error, opción de reintentar, etc.
  },
  onPaymentInProgress: function() {
    console.log('Pago con transferencia bancaria en proceso');
    // Este callback se ejecuta solo para transferencias bancarias
    // El pago puede tomar hasta 24 horas en procesarse
    // ej., mostrar mensaje informativo, enviar email de confirmación, etc.
  }
});
```

#### Método B: URL de Producto

También puedes usar una URL de producto con el formato `<span>https://app.recurrente.com/s/{organization}/{product-slug}</span>`:

View More

javascript

```javascript
RecurrenteCheckout.load({
  url: "https://app.recurrente.com/s/mi-cuenta/mi-producto",
  onSuccess: function(paymentData) {
    console.log('Pago exitoso:', paymentData);
    // Manejar pago exitoso
    // ej., redirigir a página de éxito, actualizar UI, etc.
  },
  onFailure: function(error) {
    console.log('Pago fallido:', error);
    // Manejar pago fallido
    // ej., mostrar mensaje de error, opción de reintentar, etc.
  },
  onPaymentInProgress: function() {
    console.log('Pago con transferencia bancaria en proceso');
    // Este callback se ejecuta solo para transferencias bancarias
    // El pago puede tomar hasta 24 horas en procesarse
    // ej., mostrar mensaje informativo, enviar email de confirmación, etc.
  }
});
```

 **Nota** : Reemplaza `<span>mi-cuenta</span>` con tu slug de organización y `<span>mi-producto</span>` con tu slug de producto.



## Tokenized Payments

Si quieres hacer un cobro a un cliente existente, usa tokenized payments.

### POST**Create a one time payment (amount and currency)**

**https://app.recurrente.com/api/one_time_payments/**

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Bodyformdata

**payment_method_id**

pay_m_l1aqgfoq

Encuentra este valor en el payload de un webhook exitoso, o al hacer GET /checkout en un checkout exitoso

**items[][currency]**

GTQ

La moneda a cobrar.

Posibles valores son:

* GTQ
* USD

**items[][amount_in_cents]**

3000

Monto a cobrar en centavos.

**items[][name]**

One Ripe Banana

(Opcional) El nombre del producto.

**items[][image_url]**

https://source.unsplash.com/400x400/?banana

(Opcional) URL de la imagen del producto.

**items[][quantity]**

1

(Opcional) Cantidad.

Si no incluyes una, el default es 1.

El valor mínimo es 1 y el valor máximo es 9.

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json

conn = http.client.HTTPSConnection("app.recurrente.com")
payload = json.dumps({
  "items": [
    {
      "name": "One Ripe Banana",
      "currency": "GTQ",
      "amount_in_cents": 3000,
      "image_url": "https://source.unsplash.com/400x400/?banana",
      "quantity": 1
    }
  ],
  "success_url": "https://www.google.com",
  "cancel_url": "https://www.amazon.com",
  "user_id": "us_123456",
  "metadata": {}
})
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-Type': 'application/json'
}
conn.request("POST", "/api/one_time_payments", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**201 Created**

Example Response

* **Body**
* **Headers (0)**

json

```json
{
  "id": "on_123456789",
  "status": "paid"
}
```


### POST**Create a one time payment (Product ID)**

**https://app.recurrente.com/api/checkouts/**

HEADERS

**X-PUBLIC-KEY**

{{recurrente_public_key}}

**X-SECRET-KEY**

{{recurrente_private_key}}

Bodyformdata

**payment_method_id**

pay_m_l1aqgfoq

Encuentra este valor en el payload de un webhook exitoso, o al hacer GET /checkout en un checkout exitoso

**items[][product_id]**

prod_1234567

Crea un producto primero, y luego utiliza el ID del producto.

**items[][quantity]**

1

(Opcional) Cantidad. Si no incluyes una, el default es 1. El valor mínimo es 1

Example Request

Respuesta exitosa

[ ]

View More

python

```python
import http.client
import json

conn = http.client.HTTPSConnection("app.recurrente.com")
payload = json.dumps({
  "items": [
    {
      "product_id": "prod_123456"
    }
  ],
  "metadata": {}
})
headers = {
  'X-PUBLIC-KEY': '{{recurrente_public_key}}',
  'X-SECRET-KEY': '{{recurrente_private_key}}',
  'Content-Type': 'application/json'
}
conn.request("POST", "/api/one_time_payments", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

**201 Created**

Example Response

* **Body**
* **Headers (0)**

json

```json
{
  "id": "on_123456789",
  "status": "paid"
}
```
