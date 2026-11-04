import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("png");
Config.setOverwriteOutput(true);
// Cards are flat vector-ish UI: CRF 18 keeps type edges crisp at LinkedIn's re-encode.
Config.setCrf(18);
