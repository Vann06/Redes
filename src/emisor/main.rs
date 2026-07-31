// ==========================================
// CAPA DE TRANSMISIÓN
// ==========================================
// Servicio: enviar_informacion[cite: 1]
fn enviar_informacion(trama: &str, puerto: u16) {
    // TODO: Implementar el envío de la trama a través de sockets mediante el puerto elegido[cite: 1].
}

// ==========================================
// RUIDO (Simulación)
// ==========================================
// Servicio: aplicar_ruido[cite: 1]
fn aplicar_ruido(trama: &str, probabilidad_error: f64) -> String {
    // TODO: Simular interferencias aplicando ruido a la trama con base a una probabilidad[cite: 1].
    // Recuerden que los bits de redundancia también sufren ruido[cite: 1].
    String::from(trama)
}

// ==========================================
// CAPA DE ENLACE
// ==========================================
// Servicio: calcular_integridad[cite: 1]
fn calcular_integridad(mensaje_binario: &str, algoritmo: &str) -> String {
    // TODO (Ricardo): Si el algoritmo es de detección (ej. CRC-32), calcular y concatenar aquí[cite: 1].
    
    // TODO (Vianka): Si el algoritmo es de corrección (ej. Hamming), calcular y concatenar aquí[cite: 1].
    
    String::from(mensaje_binario)
}

// ==========================================
// CAPA DE PRESENTACIÓN
// ==========================================
// Servicio: codificar_mensaje[cite: 1]
fn codificar_mensaje(texto: &str) -> String {
    // TODO: Codificar cada carácter en ASCII binario[cite: 1]. 
    // Por ejemplo, 'A' -> "01000001"[cite: 1].
    String::new()
}

// ==========================================
// CAPA DE APLICACIÓN
// ==========================================
// Servicio: solicitar_mensaje[cite: 1]
fn solicitar_mensaje() {
    // TODO: Solicitar el texto a enviar al emisor, el algoritmo de integridad y la tasa de error[cite: 1].
    // Luego, llamar a las capas inferiores en orden: Presentación -> Enlace -> Ruido -> Transmisión[cite: 1].
}

fn main() {
    println!("Iniciando Cajero Automático (Emisor)...");
    solicitar_mensaje();
}