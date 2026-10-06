import {describe,it,expect} from 'vitest';
import {tokenCoordinate} from './Chart';
describe('native-to-token display mapping',()=>{
  const words=[{id:0,text:'one',start_s:1,end_s:2,confidence:.9,review_status:'pending'},{id:1,text:'two',start_s:4,end_s:5,confidence:.9,review_status:'pending'}];
  it('never bridges a pause with fictional pitch',()=>{expect(tokenCoordinate(3,words)).toBeNull();expect(tokenCoordinate(1.5,words)).toBe(.5);expect(tokenCoordinate(4.5,words)).toBe(1.5);});
});
