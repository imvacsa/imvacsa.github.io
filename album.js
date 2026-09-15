(() => {
  const id = new URLSearchParams(location.search).get('id');
  const album = id ? albums.find(a=>a.id===id) : albums[0];
  const main = document.querySelector('#album-content');
  if (!album || !album.tracks.length) {
    main.replaceChildren(); main.hidden=false;
    const heading=document.createElement('h1');heading.textContent='앨범을 찾을 수 없어요.';
    const link=document.createElement('a');link.href='music.html';link.textContent='모든 앨범으로 돌아가기';main.append(heading,link);return;
  }
  document.title=`${album.title} | 음악과 일상`;
  const songs=album.tracks;
  const text=(selector,value)=>document.querySelector(selector).textContent=value;
  text('#album-title',album.title);text('.english',album.english||'');text('.description',album.description);
  text('#dedication',album.dedication||'음악과 일상');text('#track-heading',album.trackHeading||'수록곡');
  const total=Math.round(songs.reduce((sum,t)=>sum+t.duration,0));
  text('#album-meta',`${songs.length} TRACKS · ${Math.floor(total/60)} MIN ${String(total%60).padStart(2,'0')} SEC`);
  text('.art span',`ALBUM / ${songs.length} TRACKS`);text('.art strong',album.coverTitle||album.title);text('.art small',album.english||'');
  const art=document.querySelector('.art');art.setAttribute('aria-label',`${album.title} 앨범 표지`);
  if(album.cover){const img=document.createElement('img');img.src=album.cover;img.alt=`${album.title} 앨범 표지`;img.style.cssText='width:100%;height:100%;object-fit:cover';art.replaceChildren(img);art.style.padding='0';}
  const letter=document.querySelector('.letter');letter.replaceChildren();
  if(album.letter){const label=document.createElement('p');label.className='eyebrow';label.textContent='DEAR YOU,';const copy=document.createElement('p');copy.className='letter-copy';copy.textContent=album.letter;letter.append(label,copy);}else letter.hidden=true;
  text('footer span:first-child',album.footer||'음악과 일상');text('footer span:last-child',album.credit||'');
  let selected=0, generation=0;const player=document.querySelector('#player'),status=document.querySelector('#status');
  const fmt=s=>{const n=Math.round(s);return `${Math.floor(n/60)}:${String(n%60).padStart(2,'0')}`};
  const buttons=songs.map((song,i)=>{
    const button=document.createElement('button');button.className='track';button.setAttribute('aria-label',`${i+1}번 ${song.title} 재생`);
    const number=document.createElement('span');number.className='num';number.textContent=String(i+1).padStart(2,'0');
    const copy=document.createElement('span');copy.className='trackcopy';const title=document.createElement('strong');title.textContent=song.title;const genre=document.createElement('small');genre.textContent=song.genre||'';copy.append(title,genre);
    const duration=document.createElement('span');duration.className='duration';duration.textContent=fmt(song.duration);button.append(number,copy,duration);button.onclick=()=>select(i,true);document.querySelector('#tracklist').append(button);return button;
  });
  function select(i,autoplay=false){
    const version=++generation;selected=i;const song=songs[i];player.src=song.src;
    text('#currentTitle',song.title);text('#counter',`NOW SELECTED / ${String(i+1).padStart(2,'0')}`);text('#genre',song.genre||'');text('#lyrics',song.lyrics||'등록된 가사가 없습니다.');document.querySelector('#lyrics').scrollTop=0;
    const download=document.querySelector('#download');download.href=song.src;download.download=song.src.split('/').pop();
    buttons.forEach((button,j)=>{button.classList.toggle('active',j===i);button.setAttribute('aria-current',String(j===i))});status.textContent='';
    if(autoplay)player.play().catch(error=>{if(version===generation&&error.name!=='AbortError')status.textContent='재생 버튼을 다시 눌러 주세요.'});
  }
  document.querySelector('#start').onclick=()=>{select(0,true);document.querySelector('.playerpanel').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'center'})};
  document.querySelector('#prev').onclick=()=>select((selected+songs.length-1)%songs.length,true);
  document.querySelector('#next').onclick=()=>select((selected+1)%songs.length,true);
  player.onended=()=>{if(document.querySelector('#continuous').checked&&selected<songs.length-1)select(selected+1,true);else status.textContent='함께 들어줘서 고마워.'};
  player.onerror=()=>status.textContent='음원을 불러오지 못했어요. 새로고침하거나 원본을 저장해 주세요.';player.onplaying=()=>status.textContent='';select(0);main.hidden=false;
})();
