/* Decorative photographic water and refraction, independent of research data. */
(() => {
  const canvas=document.querySelector('[data-lake]'), scene=document.querySelector('.lake-scene');
  if(!canvas||!scene)return;
  const hero=document.querySelector('.hero'),toggle=document.querySelector('[data-lake-toggle]');
  const reduced=matchMedia('(prefers-reduced-motion: reduce)');
  let paused=false,ready=false,lost=false,time=0,last=0,raf=0,rendered=0,gl;
  try{gl=canvas.getContext('webgl',{alpha:false,antialias:false,depth:false,powerPreference:'low-power'});}catch(_){}
  function position(){
    const distance=hero?Math.min(1,Math.max(0,scrollY/(hero.offsetHeight*.8))):1;
    scene.style.opacity=String(1-distance*.91);
    document.body.classList.toggle('lake-at-top',!!hero&&scrollY<48);
    document.documentElement.style.setProperty('--reading-progress',String(scrollY/Math.max(1,document.documentElement.scrollHeight-innerHeight)));
  }
  position();addEventListener('scroll',position,{passive:true});
  if(!gl){scene.dataset.render='static';return;}
  const vertex=`attribute vec2 a;varying vec2 uv;void main(){uv=a*.5+.5;gl_Position=vec4(a,0.,1.);}`;
  const fragment=`precision highp float;
    varying vec2 uv;uniform sampler2D lake;uniform vec2 resolution;uniform float t;
    vec2 photoUV(vec2 p){
      float screen=resolution.x/resolution.y;float aspect=1664./941.;
      vec2 cover=screen>aspect?vec2(1.,aspect/screen):vec2(screen/aspect,1.);
      if(screen<1.)return (p-.5)*cover*.8+vec2(.70,.36);
      return (p-.5)*cover+vec2(.5,.5);
    }
    vec3 photo(vec2 p){return texture2D(lake,clamp(photoUV(p),.001,.999)).rgb;}
    void main(){
      vec2 p=vec2(uv.x,1.-uv.y);float aspect=resolution.x/resolution.y;
      vec2 cover=aspect>1664./941.?vec2(1.,(1664./941.)/aspect):vec2(aspect/(1664./941.),1.);
      vec2 centre=aspect<1.?(vec2(.73,.575)-vec2(.70,.36))/(cover*.8)+.5:(vec2(.73,.575)-.5)/cover+.5;
      vec2 q=(p-centre)*vec2(aspect,2.55);float r=length(q);
      float cycle=mod(t,9.);float age=cycle-1.65;float wave=0.;float slope=0.;
      for(int i=0;i<4;i++){
        float a=age-float(i)*.23;float radius=max(a,0.)*.15;
        float band=(r-radius)/.028;
        float envelope=exp(-band*band)*exp(-max(a,0.)*.5)*step(0.,a);
        wave+=sin(band*2.5)*envelope;slope+=cos(band*2.5)*envelope;
      }
      vec2 normal=q/max(r,.001);
      vec2 ambient=vec2(sin(p.y*80.+t*.65),cos(p.x*58.+p.y*36.-t*.5))*.00065;
      vec2 bend=normal*wave*.011*vec2(1./aspect,.39);
      vec3 colour=photo(p+ambient+bend);colour+=slope*.045*smoothstep(.17,.35,p.y);
      // Accelerating fall, followed by a smaller rebound at the contact point.
      float fall=clamp(cycle/1.65,0.,1.);float height=.36*(1.-fall*fall);
      float visible=1.-step(1.65,cycle);float radius=.017;
      if(age>0.&&age<.85){height=.12*sin(age/.85*3.14159);visible=1.;radius=.012;}
      vec2 dropCentre=centre-vec2(0.,height);
      vec2 d=(p-dropCentre)*vec2(aspect,1.);d.y/=1.12+fall*.12;
      float dr=length(d)/radius;
      if(dr<1.04&&visible>.5){
        float z=sqrt(max(0.,1.-dr*dr));vec3 n=normalize(vec3(d/radius,z));
        vec3 refracted=photo(dropCentre-d*.85+vec2(.04,-.22));
        float fresnel=pow(1.-z,3.);
        float highlight=pow(max(0.,dot(n,normalize(vec3(-.55,-.65,1.)))),34.);
        vec3 water=mix(refracted*.65,vec3(.82,.88,.90),fresnel*.8)+highlight*.9;
        water*=.68+.32*(1.-smoothstep(.76,.94,dr));
        colour=mix(colour,water,(1.-smoothstep(.96,1.04,dr))*visible);
      }
      float contact=exp(-r*r/.0015)*exp(-max(age,0.)*9.)*step(0.,age);
      colour=mix(colour,colour*.46,contact*.65);gl_FragColor=vec4(colour,1.);
    }`;
  function shader(type,source){const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;}
  let program;
  try{program=gl.createProgram();gl.attachShader(program,shader(gl.VERTEX_SHADER,vertex));gl.attachShader(program,shader(gl.FRAGMENT_SHADER,fragment));gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error('Lake shader link failed');}
  catch(e){console.warn('Static lake fallback:',e.message);scene.dataset.render='static';return;}
  gl.useProgram(program);
  const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);
  const a=gl.getAttribLocation(program,'a');gl.enableVertexAttribArray(a);gl.vertexAttribPointer(a,2,gl.FLOAT,false,0,0);
  const resolution=gl.getUniformLocation(program,'resolution'),clock=gl.getUniformLocation(program,'t');
  const texture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,texture);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
  function draw(){if(!ready||lost)return;gl.uniform2f(resolution,canvas.width,canvas.height);gl.uniform1f(clock,reduced.matches?3.1:time);gl.drawArrays(gl.TRIANGLES,0,6);}
  function resize(){const ratio=Math.min(devicePixelRatio||1,1.35,Math.sqrt(1100000/(innerWidth*innerHeight)));canvas.width=Math.round(innerWidth*ratio);canvas.height=Math.round(innerHeight*ratio);gl.viewport(0,0,canvas.width,canvas.height);position();draw();}
  function frame(now){if(paused||reduced.matches||document.hidden||lost){last=0;return;}if(last)time+=Math.min(now-last,100)/1000;last=now;if(now-rendered>32){draw();rendered=now;}raf=requestAnimationFrame(frame);}
  function run(){cancelAnimationFrame(raf);last=0;if(ready&&!paused&&!reduced.matches&&!document.hidden&&!lost)raf=requestAnimationFrame(frame);else draw();}
  function preference(){const stopped=paused||reduced.matches;document.documentElement.dataset.motion=stopped?'paused':'running';document.body.classList.toggle('motion-paused',stopped);if(toggle){toggle.hidden=reduced.matches||!ready||lost;toggle.textContent=paused?'Resume motion':'Pause motion';toggle.setAttribute('aria-pressed',String(paused));}dispatchEvent(new CustomEvent('motionchange',{detail:{paused:stopped}}));run();}
  const img=new Image();img.onload=()=>{gl.bindTexture(gl.TEXTURE_2D,texture);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGB,gl.RGB,gl.UNSIGNED_BYTE,img);ready=true;scene.dataset.render='live';resize();preference();};img.onerror=()=>{scene.dataset.render='static';};img.src=new URL('lake.png',import.meta.url).href;
  toggle?.addEventListener('click',()=>{paused=!paused;preference();});addEventListener('resize',resize,{passive:true});document.addEventListener('visibilitychange',run);reduced.addEventListener('change',preference);
  canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();lost=true;cancelAnimationFrame(raf);scene.dataset.render='static';if(toggle)toggle.hidden=true;});
})();
