const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
test('offline tile composition and all atlas modes render without errors',async()=>{
 const nodes={};let frame;
 function element(){return {children:[],textContent:'',checked:false,width:0,height:0,replaceChildren(){this.children=[]},append(x){this.children.push(x)},getContext(){return{clearRect(){},drawImage(){}}}};}
 for(const id of ['canvas','choices','modes','info','note','source','play','reset','loop'])nodes[id]=element();
 const c=JSON.parse(fs.readFileSync('data/catalog.json'));
 const context=vm.createContext({window:{TYRI_CATALOG:c},document:{getElementById:id=>nodes[id],createElement:()=>element()},Image:class{set src(v){queueMicrotask(()=>this.onload())}},performance:{now:()=>0},requestAnimationFrame:f=>{frame=f},TyriPlayer:require('../player.js')});
 vm.runInContext(fs.readFileSync('app.js','utf8'),context);
 for(const mode of ['reactions','directions','expressions','visemes','gestures','sources']){
  vm.runInContext(`setMode('${mode}')`,context);frame(0);await new Promise(setImmediate);frame(0);assert.match(nodes.info.textContent,/원본 프레임/);assert.ok(nodes.choices.children.length);
 }
 vm.runInContext("setMode('reactions');choose('write')",context);frame(0);await new Promise(setImmediate);frame(0);assert.match(nodes.note.textContent,/연필/);
});
