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
    // Bundled on-device model: image analysis works offline after installation.
    implementation("com.google.mlkit:image-labeling:17.0.9")
}
