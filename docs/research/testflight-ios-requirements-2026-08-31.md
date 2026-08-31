# Requisitos vigentes para llevar Burn Rate iOS a TestFlight

Verificado el **31 de agosto de 2026** (`America/Mexico_City`) contra fuentes primarias de Apple. La licencia de fuentes se contrasta además con la fuente primaria de Google Fonts. Esta nota resuelve qué exige Apple; no confirma que la cuenta, los certificados o la ficha de Burn Rate ya existan, ni decide qué audiencia, servidor o build usará el proyecto.

## Respuesta ejecutiva

- El Xcode instalado que reportó la auditoría local, **Xcode 27 beta 4, build `27A5228h`**, sí fue habilitado expresamente por Apple el 21 de julio de 2026 para TestFlight interno y externo. Al corte, la combinación beta más reciente anunciada es Xcode 27 beta 6 con SDK iOS 27 beta 6, habilitada el 25 de agosto. Apple no publica en esas entradas una fecha de revocación para beta 4, pero tampoco una matriz histórica de vigencia: el archive debe validarse y el upload debe detenerse si App Store Connect rechaza la combinación. Estas autorizaciones beta son para TestFlight, no una autorización de publicación pública. [App Store Connect Release Notes](https://developer.apple.com/help/app-store-connect/release-notes/)
- Desde el 28 de abril de 2026, toda app iOS subida a App Store Connect debe compilarse con **Xcode 26 o posterior y un SDK iOS 26 o posterior**. Esto no obliga a subir el deployment target de Burn Rate a iOS 26. [Upcoming Requirements](https://developer.apple.com/news/upcoming-requirements/), [Xcode system requirements](https://developer.apple.com/xcode/system-requirements)
- Xcode 26.6 estable está habilitado para App Store y TestFlight interno/externo. Es la alternativa de menor incertidumbre si la beta 4 instalada falla la validación o si se quiere un toolchain estable. [App Store Connect Release Notes](https://developer.apple.com/help/app-store-connect/release-notes/)
- Si el segundo iPhone pertenece a alguien que **no debe recibir acceso a App Store Connect**, la vía correcta es testing externo y el primer build pasa por TestFlight App Review. Si el tester es un usuario de App Store Connect con acceso a Burn Rate, puede ser interno y evitar ese gate. TestFlight no exige registrar el UDID del segundo iPhone. [TestFlight Overview](https://developer.apple.com/help/app-store-connect/test-a-beta-version/testflight-overview), [Locating device identifiers](https://developer.apple.com/documentation/xcode/locating-device-identifiers)
- Para conservar la posibilidad de testing externo, el archive debe distribuirse como **TestFlight & App Store**. Un build subido como **TestFlight Internal Only** queda limitado a grupos internos y no puede convertirse después en build externo o público. [Distributing your app for beta testing and releases](https://developer.apple.com/documentation/xcode/distributing-your-app-for-beta-testing-and-releases)
- Un cliente `WKWebView` no queda exento de revisión: Apple exige un backend accesible y una cuenta demo funcional, privacidad que incluya el tráfico web, y suficiente valor de app por encima de un sitio web reempaquetado. La aceptación concreta bajo la regla 4.2 es juicio de App Review. [App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)

## Requisitos confirmados por Apple

### 1. Cuenta, identidad y autoridad

1. Hace falta una membresía activa del Apple Developer Program. Una membresía vencida o acuerdos pendientes pueden pausar certificados, App Store Connect y TestFlight. [Resolving access issues](https://developer.apple.com/help/account/access/resolving-access-issues)
2. Antes del primer upload debe existir:
   - un **App ID explícito** cuyo Bundle ID coincida exactamente con el target;
   - una ficha de app en App Store Connect con plataforma, nombre, idioma principal, Bundle ID, SKU y acceso de usuarios;
   - aceptación del acuerdo vigente por el Account Holder.
   [Register an App ID](https://developer.apple.com/help/account/identifiers/register-an-app-id), [Add a new app](https://developer.apple.com/help/app-store-connect/create-an-app-record/add-a-new-app/)
3. La identidad debe coincidir de extremo a extremo: el `CFBundleIdentifier` del archive, el App ID, el provisioning profile y la ficha de App Store Connect. Para Burn Rate, el identificador observado es `mx.loo.burnrate`; verificar su existencia y propiedad es una tarea de cuenta, no un hecho resuelto por esta investigación.
4. Crear la ficha requiere Account Holder, Admin o App Manager. Subir builds permite Account Holder, Admin, App Manager o Developer. Administrar grupos externos requiere Account Holder, Admin o App Manager. Los roles limitables también necesitan acceso a la app. [Role permissions](https://developer.apple.com/help/app-store-connect/reference/account-management/role-permissions/), [Upload builds](https://developer.apple.com/help/app-store-connect/manage-builds/upload-builds), [Invite external testers](https://developer.apple.com/help/app-store-connect/test-a-beta-version/invite-external-testers)

### 2. Firma y provisioning

- Para firma manual se necesita certificado **Apple Distribution**, App ID explícito y perfil **App Store Connect**. [Certificates overview](https://developer.apple.com/help/account/create-certificates/certificates-overview), [Create an App Store Connect provisioning profile](https://developer.apple.com/help/account/provisioning-profiles/create-an-app-store-provisioning-profile/)
- Xcode 13 o posterior puede usar certificados administrados en la nube desde Organizer si no existe uno local, y `Automatically manage signing` puede gestionar el perfil. Por ello, la ausencia actual de un certificado Apple Distribution local no prueba por sí sola que la cuenta no pueda distribuir; sí obliga a verificar el Team, permisos y firma efectiva del archive. [Cloud-managed certificates](https://developer.apple.com/help/account/certificates/cloud-managed-certificates/)
- Un build elegible para TestFlight debe incluir los application identifiers dentro de su provisioning profile. [TestFlight Overview](https://developer.apple.com/help/app-store-connect/test-a-beta-version/testflight-overview)
- TestFlight y Ad Hoc son rutas distintas. El UDID es necesario para desarrollo/Ad Hoc, pero no para instalar mediante TestFlight. [Locating device identifiers](https://developer.apple.com/documentation/xcode/locating-device-identifiers)

### 3. Versión, build y procesamiento

- `CFBundleShortVersionString` es la versión visible y `CFBundleVersion` identifica la iteración del build. Bundle ID + versión + build string forman la identidad única del build en App Store Connect. [Upload builds](https://developer.apple.com/help/app-store-connect/manage-builds/upload-builds), [CFBundleVersion](https://developer.apple.com/documentation/bundleresources/information-property-list/cfbundleversion)
- Una nueva carga procesada de la misma versión necesita un build distinto. Si el upload termina en estado **Failed**, Apple permite reutilizar el mismo número en el reintento; si terminó **Complete**, incrementar el build. [View builds and metadata](https://developer.apple.com/help/app-store-connect/manage-builds/view-builds-and-metadata)
- La versión local observada `0.1.0 (1)` sólo puede usarse si esa combinación no fue procesada antes para la ficha elegida. El proyecto debe fijar versión, build y commit/ref exactos antes de archivar.
- Cada build de TestFlight está disponible durante 90 días. [TestFlight Overview](https://developer.apple.com/help/app-store-connect/test-a-beta-version/testflight-overview)

### 4. Testing interno frente a externo

| Aspecto | Interno | Externo |
| --- | --- | --- |
| Quién | Hasta 100 usuarios de App Store Connect con acceso a la app | Hasta 10,000 personas sin acceso a App Store Connect |
| Invitación | Grupo interno | Correo o enlace público; Apple exige crear antes un grupo interno |
| Revisión | No pasa por TestFlight App Review | El primer build enviado requiere revisión completa; posteriores de la misma versión pueden no requerirla |
| Gestión | Account Holder, Admin, App Manager, Developer o Marketing | Account Holder, Admin o App Manager |
| Alcance | Equipo con acceso a la cuenta/app | Testers ajenos a la cuenta |

Fuentes: [Add internal testers](https://developer.apple.com/help/app-store-connect/test-a-beta-version/add-internal-testers), [Invite external testers](https://developer.apple.com/help/app-store-connect/test-a-beta-version/invite-external-testers).

Apple permite un solo build de cada versión en Beta App Review simultáneamente y hasta seis envíos en 24 horas. Una beta externa debe estar destinada eventualmente a distribución pública y cumplir las App Review Guidelines; si Burn Rate será estrictamente privado, la política apunta a testing interno. [Invite external testers](https://developer.apple.com/help/app-store-connect/test-a-beta-version/invite-external-testers), [App Review Guidelines, 2.2](https://developer.apple.com/app-store/review/guidelines/)

### 5. Metadata beta y acceso de review

Para externos, preparar antes de enviar:

- **Beta App Description** y **Feedback Email**; pueden diferir de la futura ficha pública.
- **What to Test** por build, con el flujo que el tester debe verificar.
- contacto de review: nombre, email y teléfono en formato internacional;
- notas con URL, pasos de configuración y cualquier conducta no obvia;
- usuario y contraseña de demo que no expiren si la app exige login, además de cuentas adicionales en Notes.

Las capturas aprobadas y la categoría pueden mostrarse en la invitación, pero son opcionales en esa experiencia beta. [Provide test information](https://developer.apple.com/help/app-store-connect/test-a-beta-version/provide-test-information), [Platform version information: App Review information](https://developer.apple.com/help/app-store-connect/reference/app-information/platform-version-information/)

App Review exige que las URL y el backend estén activos y accesibles durante la revisión, y que el reviewer tenga acceso completo mediante cuenta demo o un demo mode aprobado. Para Burn Rate esto significa proporcionar una instancia reproducible, datos ficticios y credenciales en App Store Connect; nunca guardar secretos en Git o en el issue. [App Review Guidelines, 2.1](https://developer.apple.com/app-store/review/guidelines/)

### 6. `WKWebView`, servidor autohospedado y red

- Apple exige WebKit para navegar la web, pero también que la app ofrezca contenido, UI o funcionalidad por encima de un sitio reempaquetado. La shell de Burn Rate debe explicarse y probarse como producto, no asumir que `WKWebView` basta. [App Review Guidelines, 2.5.6 y 4.2](https://developer.apple.com/app-store/review/guidelines/)
- App Transport Security está activo por defecto: usar HTTPS, certificado válido y TLS 1.2 o posterior. Excepciones como `NSAllowsArbitraryLoadsInWebContent` o HTTP por dominio requieren justificación y pueden provocar revisión adicional. [Preventing insecure network connections](https://developer.apple.com/documentation/security/preventing-insecure-network-connections)
- La app debe funcionar en redes IPv6-only. [App Review Guidelines, 2.5.5](https://developer.apple.com/app-store/review/guidelines/)
- Apple no obliga a usar hosting de Apple. Sí obliga a que su reviewer pueda alcanzar el backend. Una LAN privada, VPN o allowlist sin un camino documentado no satisface por sí sola ese acceso; decidir una instancia HTTPS pública, un acceso reproducible o un demo mode es responsabilidad del proyecto.
- La privacidad de red local distingue el origen del tráfico:
  - conexiones nativas a hosts locales mediante `URLSession`, sockets o APIs construidas sobre ellos requieren permiso y `NSLocalNetworkUsageDescription`;
  - Bonjour requiere además declarar los tipos usados en `NSBonjourServices`;
  - Apple exceptúa del permiso de privacidad de red local el tráfico que se origina en `WKWebView`, `SFSafariViewController` o Safari.
  ATS es una obligación independiente. [TN3179: Understanding local network privacy](https://developer.apple.com/documentation/technotes/tn3179-understanding-local-network-privacy)

### 7. Notificaciones locales

- Las notificaciones locales y remotas que muestran alerta, sonido o badge requieren autorización mediante `UNUserNotificationCenter`, solicitada en contexto. [Asking permission to use notifications](https://developer.apple.com/documentation/usernotifications/asking-permission-to-use-notifications)
- Las locales se crean y programan en el dispositivo. La capacidad Push Notifications, el entitlement `aps-environment`, APNs y un servidor proveedor corresponden a notificaciones remotas. Por tanto, una implementación puramente local no requiere Push; cualquier bridge web→nativo sí debe validarse en Release y en dispositivo físico. [User Notifications](https://developer.apple.com/documentation/usernotifications/), [Registering your app with APNs](https://developer.apple.com/documentation/usernotifications/registering-your-app-with-apns)

### 8. Privacy manifest, App Privacy y política

Son tres capas distintas:

1. **`PrivacyInfo.xcprivacy` dentro del bundle.** Debe declarar cada Required Reason API usada por el código propio; SDKs cubiertos deben aportar su manifest y, cuando aplica, firma. Manifests inválidos son rechazados por App Store Connect. [Privacy manifest files](https://developer.apple.com/documentation/bundleresources/privacy-manifest-files), [Adding a privacy manifest](https://developer.apple.com/documentation/bundleresources/adding-a-privacy-manifest-to-your-app-or-third-party-sdk), [Third-party SDK requirements](https://developer.apple.com/support/third-party-SDK-requirements/)
2. **App Privacy en App Store Connect.** Debe cubrir las prácticas del cliente, servidor y terceros. Apple dice expresamente que los datos recogidos mediante tráfico de un web view se declaran salvo que la persona navegue la web abierta. “Collect” significa transmitir fuera del dispositivo y conservar de forma accesible por más tiempo del necesario para servir la petición en tiempo real. [App privacy details](https://developer.apple.com/app-store/app-privacy-details/)
3. **Política de privacidad.** La URL es obligatoria para iOS, y la política debe estar también accesible dentro de la app, explicando colección, uso, terceros, retención, borrado y revocación. [Manage app privacy](https://developer.apple.com/help/app-store-connect/manage-app-information/manage-app-privacy/), [App Review Guidelines, 5.1.1](https://developer.apple.com/app-store/review/guidelines/)

Apple presenta las respuestas de App Privacy como requisito para enviar una app nueva o una actualización al **App Store**; su documentación de TestFlight no las enumera como gate mecánico para subir o distribuir un build interno. Eso no elimina la obligación de un manifest válido en el binario ni la revisión de privacidad, política y acceso cuando se elige la ruta externa. [App privacy details](https://developer.apple.com/app-store/app-privacy-details/), [TestFlight Overview](https://developer.apple.com/help/app-store-connect/test-a-beta-version/testflight-overview)

La auditoría local reportó un manifest con `UserDefaults`/`CA92.1`. Apple autoriza ese motivo sólo para leer/escribir defaults accesibles a la propia app. Eso no prueba que el manifest esté completo ni que App Privacy pueda responder “no data collected”. El archive elegido debe generar un Privacy Report y contrastarse con el código y el servidor. [NSPrivacyAccessedAPIType](https://developer.apple.com/documentation/bundleresources/app-privacy-configuration/nsprivacyaccessedapitypes/nsprivacyaccessedapitype)

Para Burn Rate, declarar `Other Financial Info`, `User ID`, interacción, diagnóstico u otros tipos depende de qué datos persista realmente el servidor, sus logs, analytics y autenticación. No se puede fijar la respuesta sin ese inventario. Si la app permite crear cuentas, Apple exige iniciar la eliminación de la cuenta dentro de la app. [App privacy details](https://developer.apple.com/app-store/app-privacy-details/), [App Review Guidelines, 5.1.1(v)](https://developer.apple.com/app-store/review/guidelines/)

### 9. Export compliance y cifrado

- Cada build debe resolver export compliance antes de quedar disponible. Si falta la declaración, aparece **Missing Compliance**. [Provide export compliance information for beta builds](https://developer.apple.com/help/app-store-connect/test-a-beta-version/provide-export-compliance-information-for-beta-builds/)
- Apple indica que la criptografía del sistema, por ejemplo HTTPS mediante networking del OS, típicamente está exenta de subir documentación. Sólo tras confirmar que la app y todas sus librerías no implementan cifrado no exento se puede usar `ITSAppUsesNonExemptEncryption = NO`. Sin esa clave, App Store Connect presenta el cuestionario en cada carga. [Complying with Encryption Export Regulations](https://developer.apple.com/documentation/security/complying-with-encryption-export-regulations), [ITSAppUsesNonExemptEncryption](https://developer.apple.com/documentation/bundleresources/information-property-list/itsappusesnonexemptencryption)
- Si usa cifrado no exento, hay que cargar la documentación, esperar aprobación y asociar el código resultante antes de Beta App Review. Apple evalúa caso por caso. La posible declaración anual de autoclasificación de EE. UU. queda fuera de una conclusión automática y debe resolverla quien asuma la responsabilidad legal.

### 10. Derechos de fuentes y otros recursos

- Apple exige que iconos, imágenes, texto, fuentes y cualquier material protegido sean propios o estén licenciados. Puede solicitar documentación de autorización. [App Review Guidelines, 2.3.9 y 5.2](https://developer.apple.com/app-store/review/guidelines/)
- Una fuente custom puede incluirse mediante `UIAppFonts`, pero Apple no concede derechos de redistribución por permitir técnicamente el bundle. [Adding a custom font to your app](https://developer.apple.com/documentation/uikit/adding-a-custom-font-to-your-app)
- Google afirma que **las familias efectivamente distribuidas por Google Fonts** se publican bajo licencias open source y pueden usarse comercialmente. Esa afirmación no basta para inferir la licencia de un archivo llamado “Google Sans”: hay que identificar archivo, origen, versión y licencia exactos. [Google Fonts](https://developers.google.com/fonts)
- Para cada fuente embebida, conservar origen, licencia y notices exigidos. Si no hay evidencia de redistribución/embedding, obtener permiso o sustituirla por una fuente de sistema o una familia con licencia comprobada antes del archive.

## Riesgos de review que no son requisitos mecánicos

- **Regla 4.2:** Apple no publica un umbral objetivo de “suficiente funcionalidad nativa”. La aceptación del wrapper depende del build y de la explicación al reviewer.
- **Producto financiero:** la regla 3.2.1(viii) dice que apps de financial trading, investing o money management deberían ser enviadas por la institución financiera que presta esos servicios. Apple no aclara si un ledger personal autohospedado que no custodia ni mueve dinero entra en esa categoría. Las Review Notes deben describir con precisión lo que Burn Rate no hace; la clasificación final corresponde a Apple. [App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- Apple no publica rangos IP estables para allowlisting de reviewers. No diseñar el acceso suponiendo que podrán entrar a una LAN, VPN o Cloudflare Access sin instrucciones y credenciales.
- La tabla genérica de “Upload builds” conserva mínimos antiguos que contradicen el requisito fechado de abril de 2026. Para el corte de esta nota se usa el requisito fechado y las Release Notes específicas. [Upload builds](https://developer.apple.com/help/app-store-connect/manage-builds/upload-builds), [Upcoming Requirements](https://developer.apple.com/news/upcoming-requirements/)

## Decisiones que siguen siendo del proyecto

1. Audiencia: tester interno con acceso a App Store Connect o externo sujeto a Beta App Review y a la intención de distribución pública.
2. Toolchain: validar la beta 4 instalada o instalar una combinación estable/actual anunciada por Apple.
3. Identidad y autoridad: Team, Account Holder, roles, acuerdos, App ID, ficha y mecanismo de firma.
4. Candidato: commit/ref, `0.1.0 (1)` u otra versión/build y correspondencia con la versión del servidor.
5. Conectividad: instancia, HTTPS/LAN, cuenta demo, datos ficticios, disponibilidad y acceso del reviewer.
6. Expediente: respuestas exactas de App Privacy/export compliance, política, metadata beta, Review Notes y licencias de recursos.
7. Gates: pruebas Release en dispositivo, archive firmado, Validate App, procesamiento **Complete**, invitación, instalación, primer arranque y smoke contra el servidor.

La investigación no autoriza archive, upload, invitaciones ni publicación. Esas acciones deben partir del candidato aprobado y detenerse ante firma inesperada, warning no explicado, `Missing Compliance`, upload rechazado, backend inaccesible o cualquier diferencia entre archive, ficha y commit.
