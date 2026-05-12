// electron/notarize.js
const { notarize } = require("@electron/notarize");

exports.default = async function notarizeMacApp(context) {
  const { electronPlatformName, appOutDir } = context;
  if (electronPlatformName !== "darwin") return;

  if (process.env.SKIP_NOTARIZE === "true") {
    console.log("notarize: skipped (SKIP_NOTARIZE=true)");
    return;
  }

  const appName = context.packager.appInfo.productFilename;
  const appPath = `${appOutDir}/${appName}.app`;

  console.log(`notarize: submitting ${appPath} …`);
  const before = Date.now();
  await notarize({
    tool: "notarytool",
    appBundleId: "com.n8nrep.desktop",
    appPath,
    appleId: process.env.APPLE_ID,
    appleIdPassword: process.env.APPLE_ID_PASSWORD,
    teamId: process.env.APPLE_TEAM_ID,
  });
  const elapsed = ((Date.now() - before) / 1000).toFixed(1);
  console.log(`notarize: completed in ${elapsed}s`);
};
