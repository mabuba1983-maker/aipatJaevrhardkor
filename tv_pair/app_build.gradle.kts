plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }
android {
    namespace = "ai.nuwaa"
    compileSdk = 34
    defaultConfig { applicationId = "ai.nuwaa"; minSdk = 24; targetSdk = 34; versionCode = 1; versionName = "0.1" }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    kotlinOptions { jvmTarget = "17" }
    androidResources { noCompress += "bin" }
}

dependencies {
    // Only new dependency in the whole app. Needed because plain Android has no built-in WebSocket
    // client — this is what TvLink.kt uses to talk to the pairing server (same protocol as server.ts).
    // Free, no account, no API key; one of the most widely used Android libraries there is.
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
}
