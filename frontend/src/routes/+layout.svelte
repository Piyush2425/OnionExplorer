<script>
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>OnionExplorer — Dark Web Threat Intelligence</title>
</svelte:head>

{@render children()}
