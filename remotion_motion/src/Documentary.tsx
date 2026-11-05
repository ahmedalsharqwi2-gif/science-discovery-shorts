import {staticFile} from 'remotion';
import {loadFont} from '@remotion/fonts';
loadFont({family:'Arabic',url:staticFile('fonts/Arabic-Regular.ttf'),weight:'400'});
loadFont({family:'Arabic',url:staticFile('fonts/Arabic-Bold.ttf'),weight:'700'});
export {LockedFilm as Documentary} from './LockedFilm';
