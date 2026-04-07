import path from "path";
import fs_extra from "fs-extra";

;// CONCATENATED MODULE: external "path"

;// CONCATENATED MODULE: external "fs-extra"

;// CONCATENATED MODULE: ./src/common/node-utils.ts


const fileExistsWithCaseSync = (filepath)=>{
    const dir = path.dirname(filepath);
    if (filepath === '/' || filepath === '.') {
        return true;
    }
    const filenames = fs_extra.readdirSync(dir);
    if (filenames.indexOf(path.basename(filepath)) === -1) {
        return false;
    }
    return fileExistsWithCaseSync(dir);
};
const fixPrefetchPath = (exposePath)=>{
    const pathExt = [
        '.js',
        '.ts'
    ];
    const extReg = /\.(ts|js|tsx|jsx)$/;
    if (extReg.test(exposePath)) {
        return pathExt.map((ext)=>exposePath.replace(extReg, `.prefetch${ext}`));
    } else {
        return pathExt.map((ext)=>exposePath + `.prefetch${ext}`);
    }
};

export { fileExistsWithCaseSync, fixPrefetchPath };
