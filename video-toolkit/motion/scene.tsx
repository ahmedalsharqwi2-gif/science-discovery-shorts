import {makeScene2D, Circle} from '@motion-canvas/2d';
import {createRef} from '@motion-canvas/core';
export default makeScene2D(function* (view) {
  const circle=createRef<Circle>();
  view.add(<Circle ref={circle} size={240} fill={'#cda65c'}/>);
  yield* circle().scale(1.2,1);
  yield* circle().scale(1,1);
});
