(() => {
  const duration = seconds => { const total = Math.round(seconds); return `${Math.floor(total/60)}분 ${String(total%60).padStart(2,'0')}초`; };
  function element(tag, className, text) {
    const node = document.createElement(tag); node.className = className || '';
    if (text !== undefined) node.textContent = text;
    return node;
  }
  for (const list of document.querySelectorAll('[data-album-list]')) {
    for (const [index, album] of albums.entries()) {
      const link = element('a','album-card');
      link.href = `album.html?id=${encodeURIComponent(album.id)}`;
      const art = element('div','album-cover'); art.setAttribute('aria-hidden','true');
      if (album.cover) { const img=element('img');img.src=album.cover;img.alt='';img.loading='lazy';art.classList.add('has-image');art.append(img); }
      else art.append(element('span','',`ALBUM ${String(index+1).padStart(2,'0')}`),element('strong','',album.coverTitle || album.title),element('small','',album.english || ''));
      const copy=element('div','album-copy');const bottom=element('div','album-bottom');
      bottom.append(element('span','',`${album.tracks.length}곡 · ${duration(album.tracks.reduce((sum,t)=>sum+t.duration,0))}`),element('span','','앨범 듣기 ↗'));
      copy.append(element('h3','',album.title),element('p','',album.description),bottom);link.append(art,copy);list.append(link);
    }
  }
  const count=document.querySelector('#album-count');if(count)count.textContent=`${albums.length}개의 앨범`;
})();
