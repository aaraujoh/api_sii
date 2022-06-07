# api_sii
API que permite la conexion con SII Chile


# Ejemplo de prueba

``` 
curl -i -H "Content-type: application/json" http://localhost:5000/upload -d@sample_data.json 
``` 


Para probar la funcion si utilizar la api:



``` 
python  mysii.py <path al archivo json>
``` 