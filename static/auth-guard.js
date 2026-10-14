
document.addEventListener("DOMContentLoaded", async () => {
    try {
        const client = await window.initializeSupabase();

        const { data, error } = await client.auth.getSession();

        if (error || !data.session) {
            window.location.replace("/login");
            return;
        }

        window.currentSupabaseSession = data.session;

        client.auth.onAuthStateChange((event, session) => {
            if (!session) {
                window.location.replace("/login");
            } else {
                window.currentSupabaseSession = session;
            }
        });

        const logoutButton = document.getElementById("logout-button");

        if (logoutButton) {
            logoutButton.addEventListener("click", async () => {
                logoutButton.disabled = true;

                const { error: logoutError } = await client.auth.signOut();

                if (logoutError) {
                    logoutButton.disabled = false;
                    alert("Logout failed. Please try again.");
                    return;
                }

                window.location.replace("/login");
            });
        }
    } catch (error) {
        console.error("Authentication initialization failed:", error);
        window.location.replace("/login");
    }
});
