
window.supabaseClient = null;
window.supabaseInitPromise = null;

window.initializeSupabase = function () {
    if (window.supabaseClient) {
        return Promise.resolve(window.supabaseClient);
    }

    if (window.supabaseInitPromise) {
        return window.supabaseInitPromise;
    }

    window.supabaseInitPromise = (async () => {
        const response = await fetch("/api/config");

        if (!response.ok) {
            throw new Error("Could not load Supabase configuration.");
        }

        const config = await response.json();

        if (!config.supabase_url || !config.supabase_publishable_key) {
            throw new Error("Supabase configuration is missing.");
        }

        window.supabaseClient = window.supabase.createClient(
            config.supabase_url,
            config.supabase_publishable_key,
            {
                auth: {
                    persistSession: true,
                    autoRefreshToken: true,
                    detectSessionInUrl: true
                }
            }
        );

        return window.supabaseClient;
    })();

    
return window.supabaseInitPromise.catch((error) => {
    window.supabaseInitPromise = null;
    throw error;
});

};
