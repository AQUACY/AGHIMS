const { config } = require("./config");
const { createApp } = require("./app");
const { startReminderLoop } = require("./reminders");

createApp()
  .then((app) => {
    const server = app.listen(config.port, config.host, () => {
      console.log(`License Portal v2 listening on http://${config.host}:${config.port}`);
      console.log(`UI: ${config.publicBaseUrl}/`);
      startReminderLoop();
    });
    server.keepAliveTimeout = 65000;
  })
  .catch((err) => {
    console.error("Failed to start license portal v2:", err);
    process.exit(1);
  });
