import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import matplotlib.pyplot as plt

# UNIVERSOS DE DISCURSO

# Edad: 18 a 100 años
edad = ctrl.Antecedent(np.arange(18, 101, 1), 'edad')
# Riesgo Laboral: 0 a 100
riesgo_lab = ctrl.Antecedent(np.arange(0, 101, 1), 'riesgo_laboral')
# Índice de Salud: 0 a 100
salud = ctrl.Antecedent(np.arange(0, 101, 1), 'salud')
# Estilo de Vida: 0 a 100
estilo_vida = ctrl.Antecedent(np.arange(0, 101, 1), 'estilo_vida')

# Salida: Perfil de Riesgo (0 a 100)
perfil_riesgo = ctrl.Consequent(np.arange(0, 101, 1), 'perfil_riesgo')


# FUNCIONES DE PERTENENCIA

# Edad: Trapezoidal y Gaussiana
edad['joven'] = fuzz.trapmf(edad.universe, [18, 18, 25, 35])
edad['adulto'] = fuzz.gaussmf(edad.universe, 50, 10)
edad['anciano'] = fuzz.trapmf(edad.universe, [60, 75, 100, 100])

# Riesgo Laboral: Triangular, Gaussiana y Trapezoidal
riesgo_lab['minimo'] = fuzz.trimf(riesgo_lab.universe, [0, 0, 25])
riesgo_lab['bajo'] = fuzz.gaussmf(riesgo_lab.universe, 25, 8) 
riesgo_lab['medio'] = fuzz.trimf(riesgo_lab.universe, [20, 50, 80])
riesgo_lab['alto'] = fuzz.gaussmf(riesgo_lab.universe, 75, 8)
riesgo_lab['maximo'] = fuzz.trapmf(riesgo_lab.universe, [70, 90, 100, 100])

# Salud: Trapezoidal, Gaussiana, Triangular
salud['critico'] = fuzz.trapmf(salud.universe, [0, 0, 20, 40])
salud['estable'] = fuzz.gaussmf(salud.universe, 50, 15)
salud['excelente'] = fuzz.trimf(salud.universe, [60, 100, 100])

# Estilo de Vida
# Base para saludable
base_saludable = fuzz.gaussmf(estilo_vida.universe, 80, 12)

estilo_vida['riesgoso'] = fuzz.trapmf(estilo_vida.universe, [0, 0, 20, 40])
estilo_vida['moderado'] = fuzz.trimf(estilo_vida.universe, [30, 50, 70])

# Modificadores sobre la base de saludable
estilo_vida['saludable'] = base_saludable
estilo_vida['muy_saludable'] = np.power(base_saludable, 2) # Concentración
estilo_vida['poco_saludable'] = np.sqrt(base_saludable)    # Dilatación

# Perfil de Riesgo (Salida)
perfil_riesgo['bajo'] = fuzz.trimf(perfil_riesgo.universe, [0, 0, 30])
perfil_riesgo['medio'] = fuzz.gaussmf(perfil_riesgo.universe, 50, 12)
perfil_riesgo['alto'] = fuzz.trimf(perfil_riesgo.universe, [60, 80, 100])
perfil_riesgo['muy_alto'] = fuzz.trapmf(perfil_riesgo.universe, [80, 90, 100, 100])

# REGLAS DIFUSAS
reglas = [
    # SI (Edad es joven) Y (Salud excelente) Y NO (Riesgo laboral máximo) ENTONCES Perfil bajo
    ctrl.Rule(edad['joven'] & salud['excelente'] & ~riesgo_lab['maximo'], perfil_riesgo['bajo']),
    
    # SI (Salud crítico) O (Riesgo laboral máximo) ENTONCES Perfil muy alto
    ctrl.Rule(salud['critico'] | riesgo_lab['maximo'], perfil_riesgo['muy_alto']),
    
    # SI (Edad adulto) Y (Estilo moderado O saludable) Y NO (Salud crítico) ENTONCES Perfil medio
    ctrl.Rule(edad['adulto'] & (estilo_vida['moderado'] | estilo_vida['saludable']) & ~salud['critico'], perfil_riesgo['medio']),
    
    # SI (Edad joven) Y NO (Estilo riesgoso) Y NO (Riesgo laboral alto) ENTONCES Perfil bajo
    ctrl.Rule(edad['joven'] & ~estilo_vida['riesgoso'] & ~riesgo_lab['alto'], perfil_riesgo['bajo']),
    
    # SI (Edad anciano) O (Salud estable Y Estilo poco saludable) ENTONCES Perfil alto
    ctrl.Rule(edad['anciano'] | (salud['estable'] & estilo_vida['poco_saludable']), perfil_riesgo['alto']),
    
    # SI (Edad joven) Y (Salud estable) Y (Riesgo laboral medio) ENTONCES Perfil medio
    ctrl.Rule(edad['joven'] & salud['estable'] & riesgo_lab['medio'], perfil_riesgo['medio']),
    
    # SI (Edad adulto) Y (Salud excelente) Y NO (Estilo riesgoso O poco saludable) Y (Riesgo laboral mínimo) ENTONCES Perfil medio
    ctrl.Rule(edad['adulto'] & salud['excelente'] & ~(estilo_vida['riesgoso'] | estilo_vida['poco_saludable']) & riesgo_lab['minimo'], perfil_riesgo['medio']),
    
    # SI (Edad joven) Y (Salud crítico O Estilo riesgoso) Y NO (Riesgo laboral mínimo) ENTONCES Perfil muy alto
    ctrl.Rule(edad['joven'] & (salud['critico'] | estilo_vida['riesgoso']) & ~riesgo_lab['minimo'], perfil_riesgo['muy_alto']),
    
    # SI (Edad anciano) Y (Salud excelente Y Estilo muy saludable) Y NO (Riesgo laboral alto O máximo) ENTONCES Perfil alto
    ctrl.Rule(edad['anciano'] & (salud['excelente'] & estilo_vida['muy_saludable']) & ~(riesgo_lab['alto'] | riesgo_lab['maximo']), perfil_riesgo['alto'])
]

# SISTEMA DE CONTROL Y SIMULACIÓN
sistema_control = ctrl.ControlSystem(reglas)
simulacion = ctrl.ControlSystemSimulation(sistema_control)

# JUSTIFICAR DEFUZZIFICACIÓN

# PRUEBA
simulacion.input['edad'] = 22
simulacion.input['riesgo_laboral'] = 10
simulacion.input['salud'] = 90
simulacion.input['estilo_vida'] = 85

simulacion.compute()
print(f"Resultado del Perfil de Riesgo: {simulacion.output['perfil_riesgo']:.2f}")

# VISUALIZACIÓN
edad.view()
riesgo_lab.view()
salud.view()
estilo_vida.view()
perfil_riesgo.view(sim=simulacion)
plt.show()