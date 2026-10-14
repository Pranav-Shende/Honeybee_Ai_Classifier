
document.addEventListener("DOMContentLoaded", async () => {
    const message = document.getElementById("auth-message");

    try {
        await initializeSupabase();
    } catch (error) {
        message.textContent = "Unable to connect to authentication. Check your configuration.";
        console.error(error);
        return;
    }

    const client = window.supabaseClient;
    const loginForm = document.getElementById("login-form");
    const registerForm = document.getElementById("register-form");

    if (loginForm) {
        loginForm.addEventListener("submit", async (event) => {
            event.preventDefault();

            const button = document.getElementById("login-button");
            button.disabled = true;
            message.textContent = "Signing in...";

            try {
                const { error } = await client.auth.signInWithPassword({
                    email: document.getElementById("email").value.trim(),
                    password: document.getElementById("password").value
                });

                if (error) throw error;

                window.location.href = "/";
            } catch (error) {
                message.textContent = error.message || "Login failed.";
            } finally {
                button.disabled = false;
            }
        });
    }

    if (registerForm) {
        registerForm.addEventListener("submit", async (event) => {
            event.preventDefault();

            const button = document.getElementById("register-button");
            button.disabled = true;
            message.textContent = "Creating account...";

            try {
                const { data, error } = await client.auth.signUp({
                    email: document.getElementById("email").value.trim(),
                    password: document.getElementById("password").value
                });

                if (error) throw error;

                if (data.session) {
                    message.textContent = "Account created successfully!";
                    window.location.href = "/";
                } else {
                    message.textContent =
                        "Account created. Check your email to confirm your address, then sign in.";
                }
            } catch (error) {
                message.textContent = error.message || "Registration failed.";
            } finally {
                button.disabled = false;
            }
        });
    }
});
