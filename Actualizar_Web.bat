@echo off
echo 🚀 Preparando los datos para subir a la web...
cd "C:\Users\Usuario\Desktop\ADARVE JUV D.H\App_Rendimiento_Futbol"
git add .
git commit -m "Actualizacion automatica de datos desde el Boton Magico"
git push
echo ✅ ¡Datos subidos con exito! La web se actualizara en unos segundos.
timeout /t 5
exit